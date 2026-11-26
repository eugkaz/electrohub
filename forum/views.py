from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, HttpResponseBadRequest, Http404, HttpResponseForbidden
from .models import *
from django.db.models import Count, Q
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserPostForm, AnswerForm
from django.template.loader import render_to_string
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.urls import reverse

ANSWERS_PER_LOAD = 10
POSTS_PER_PAGE_MAIN = 15

def forum(request):
   categories = Category.objects.annotate(num_posts=Count('posts')).order_by('name')
   latest_blogs = BlogPost.objects.order_by('-timestamp')[:3]
   latest_topics_sidebar = UserPost.objects.order_by('-last_activity')[:5]
   all_user_posts_list = UserPost.objects.select_related('author__user', 'category') \
                                     .prefetch_related('answers', 'views') \
                                     .order_by('-last_activity')
   paginator = Paginator(all_user_posts_list, POSTS_PER_PAGE_MAIN)
   page_number = request.GET.get('page')
   try:
       page_obj = paginator.get_page(page_number)
   except PageNotAnInteger:
       page_obj = paginator.get_page(1)
   except EmptyPage:
       page_obj = paginator.get_page(paginator.num_pages)
   total_topics_count = UserPost.objects.count()
   total_posts_count = total_topics_count + Answer.objects.count()
   total_users_count = User.objects.filter(is_active=True).count()
   context = {
       'page_obj': page_obj, 'paginator': paginator, 'latest_blogs': latest_blogs,
       'latest_topics': latest_topics_sidebar, 'categories': categories,
       'total_topics': total_topics_count, 'total_posts': total_posts_count,
       'total_users': total_users_count,
   }
   return render(request, 'forum/forum-main.html', context)

@login_required(login_url='login')
def userPost(request):
   if request.method == 'POST':
       form = UserPostForm(request.POST, request.FILES)
       if form.is_valid():
           author, created = Author.objects.get_or_create(user=request.user)
           post = form.save(commit=False)
           post.author = author
           post.save()
           messages.success(request, "Тему успішно створено!")
           return redirect(post.get_absolute_url())
       else:
           messages.error(request, "Будь ласка, виправте помилки у формі.")
   else:
       form = UserPostForm()
   categories = Category.objects.all()
   context = {'form': form, 'categories': categories}
   return render(request, 'forum/user-post.html', context)

def postTopic(request, pk):
    topic = get_object_or_404(
        UserPost.objects.select_related('author__user', 'category'),
        pk=pk
    )
    if request.user.is_authenticated:
        PostView.objects.get_or_create(user=request.user, user_post=topic)
    view_count = topic.topic_view_count

    top_level_answers_query = Answer.objects.filter(
        user_post=topic,
        parent__isnull=True
    ).select_related('user', 'user__profile') \
     .prefetch_related(
        'upvotes', 'downvotes', 'replies',
        'replies__user', 'replies__user__profile',
        'replies__upvotes', 'replies__downvotes',
    )
    
    paginator = Paginator(top_level_answers_query, ANSWERS_PER_LOAD)
    initial_answers_page = paginator.get_page(1)
    initial_answers = initial_answers_page.object_list
    has_more_answers = initial_answers_page.has_next()

    if request.method == "POST" and request.user.is_authenticated:
        answer_form = AnswerForm(request.POST, request.FILES)
        if answer_form.is_valid():
            try:
                new_answer = answer_form.save(commit=False)
                new_answer.user = request.user
                new_answer.user_post = topic
                parent_id = request.POST.get('parent_id')
                if parent_id:
                    try:
                        parent_answer = Answer.objects.get(id=parent_id, user_post=topic)
                        new_answer.parent = parent_answer
                    except Answer.DoesNotExist:
                        messages.error(request, 'Неможливо відповісти на неіснуючий коментар.')
                        context = get_topic_detail_context(request, topic, initial_answers, has_more_answers, view_count, answer_form)
                        return render(request, 'forum/topic-detail.html', context)
                new_answer.save()
                messages.success(request, 'Вашу відповідь успішно опубліковано!')
                redirect_url = reverse('topic-detail', kwargs={'pk': pk}) + f'#answer-{new_answer.id}'
                return redirect(redirect_url)
            except Exception as e:
                print(f"Error saving answer: {e}")
                messages.error(request, 'Сталася помилка при збереженні відповіді.')
                answer_form = AnswerForm()
        else:
            messages.error(request, 'Будь ласка, виправте помилки у формі.')
    elif request.method == "POST" and not request.user.is_authenticated:
        messages.error(request, 'Будь ласка, увійдіть, щоб залишити відповідь.')
        return redirect(f"{reverse('login')}?next={request.path}")
    else:
        answer_form = AnswerForm()

    context = get_topic_detail_context(request, topic, initial_answers, has_more_answers, view_count, answer_form)
    return render(request, 'forum/topic-detail.html', context)

def get_topic_detail_context(request, topic, initial_answers, has_more_answers, view_count, answer_form):
   categories = Category.objects.annotate(num_posts=Count('posts')).order_by('name')
   related_topics = []
   if topic.category:
       related_topics = UserPost.objects.filter(category=topic.category) \
                                       .exclude(pk=topic.pk) \
                                       .order_by('-last_activity')[:5]
   return {
       'topic': topic, 'answers': initial_answers, 'has_more_answers': has_more_answers,
       'answers_per_load': ANSWERS_PER_LOAD, 'answer_form': answer_form,
       'categories': categories, 'related_topics': related_topics,
       'topic_view_count': view_count,
   }

def load_more_answers(request, pk):
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return HttpResponseBadRequest("Invalid request type")
    topic = get_object_or_404(UserPost, pk=pk)
    try:
        page = int(request.GET.get('page', 2))
        if page < 1: page = 1
    except ValueError:
        return JsonResponse({'html': '', 'has_more': False, 'error': 'Invalid page number'}, status=400)

    top_level_answers_query = Answer.objects.filter(
        user_post=topic, parent__isnull=True
    ).select_related('user', 'user__profile') \
     .prefetch_related(
        'upvotes', 'downvotes', 'replies',
        'replies__user', 'replies__user__profile',
        'replies__upvotes', 'replies__downvotes'
    )
    paginator = Paginator(top_level_answers_query, ANSWERS_PER_LOAD)
    page_to_load = page
    if page_to_load > paginator.num_pages:
        return JsonResponse({'html': '', 'has_more': False})
    try:
        page_obj = paginator.page(page_to_load)
    except EmptyPage:
        return JsonResponse({'html': '', 'has_more': False})
    answers_html = render_to_string(
        'forum/partials/answers_list.html',
        {'answers': page_obj.object_list, 'request': request, 'topic': topic}
    )
    return JsonResponse({'html': answers_html, 'has_more': page_obj.has_next()})

@login_required(login_url='login')
def edit_answer(request, answer_pk):
   answer = get_object_or_404(Answer.objects.select_related('user', 'user_post'), pk=answer_pk)
   if request.user != answer.user:
       messages.error(request, "Ви не можете редагувати цю відповідь.")
       return redirect(answer.user_post.get_absolute_url())
   if request.method == 'POST':
       form = AnswerForm(request.POST, request.FILES, instance=answer)
       if form.is_valid():
           form.save()
           messages.success(request, "Відповідь успішно оновлено.")
           redirect_url = reverse('topic-detail', kwargs={'pk': answer.user_post.pk}) + f'#answer-{answer.pk}'
           return redirect(redirect_url)
       else:
           messages.error(request, "Будь ласка, виправте помилки у формі.")
   else:
       form = AnswerForm(instance=answer)
   context = {'form': form, 'answer': answer}
   return render(request, 'forum/edit_answer.html', context)

@login_required(login_url='login')
def delete_answer(request, answer_pk):
   answer = get_object_or_404(Answer.objects.select_related('user', 'user_post'), pk=answer_pk)
   post_pk = answer.user_post.pk
   if request.user != answer.user:
        messages.error(request, "Ви не можете видалити цю відповідь.")
        return redirect(answer.user_post.get_absolute_url())
   if request.method == 'POST':
       answer.delete()
       messages.success(request, "Відповідь успішно видалено.")
       return redirect('topic-detail', pk=post_pk)
   else:
       context = {'answer': answer}
       return render(request, 'forum/delete_answer_confirm.html', context)

@login_required(login_url='login')
def userDashboard(request):
   author, created = Author.objects.get_or_create(user=request.user)
   topic_posted = UserPost.objects.filter(author=author).order_by('-date_created')
   ans_posted = Answer.objects.filter(user=request.user).order_by('-date_created')
   categories = Category.objects.annotate(num_posts=Count('posts')).order_by('name')
   context = {
       'topic_posted': topic_posted, 'ans_posted': ans_posted,
       'topic_count': topic_posted.count(), 'ans_count': ans_posted.count(),
       'categories': categories,
   }
   return render(request, 'forum/user-dashboard.html', context)

def searchView(request):
   search_query = request.GET.get('q', '').strip()
   queryset = UserPost.objects.none()
   q_count = 0
   if search_query:
       queryset = UserPost.objects.select_related('author__user', 'category').filter(
           Q(title__icontains=search_query) | Q(description__icontains=search_query)
       ).distinct().order_by('-last_activity')
       q_count = queryset.count()
   else:
       messages.error(request, "Будь ласка, введіть ключове слово для пошуку.")
   paginator = Paginator(queryset, POSTS_PER_PAGE_MAIN)
   page_number = request.GET.get('page')
   try:
       page_obj = paginator.get_page(page_number)
   except PageNotAnInteger:
       page_obj = paginator.get_page(1)
   except EmptyPage:
       page_obj = paginator.get_page(paginator.num_pages)
   categories = Category.objects.annotate(num_posts=Count('posts')).order_by('name')
   context = {
       'page_obj': page_obj, 'paginator': paginator, 'search_query': search_query,
       'q_count': q_count, 'categories': categories,
   }
   return render(request, 'forum/search-result.html', context)

@login_required(login_url='login')
def upvote(request):
   if request.method != 'POST':
       return HttpResponseBadRequest("Invalid request method")
   answer = get_object_or_404(Answer, id=request.POST.get('answer_id'))
   user = request.user
   has_downvoted = answer.downvotes.filter(id=user.id).exists()
   has_upvoted = answer.upvotes.filter(id=user.id).exists()
   if has_upvoted:
       answer.upvotes.remove(user)
   else:
       answer.upvotes.add(user)
       if has_downvoted:
           answer.downvotes.remove(user)
   if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
       return JsonResponse({
           'upvotes': answer.upvotes.count(), 'downvotes': answer.downvotes.count(),
           'user_upvoted': answer.upvotes.filter(id=user.id).exists(),
           'user_downvoted': answer.downvotes.filter(id=user.id).exists(),
       })
   else:
       redirect_url = reverse('topic-detail', kwargs={'pk': answer.user_post.pk}) + f'#answer-{answer.pk}'
       return redirect(redirect_url)

@login_required(login_url='login')
def downvote(request):
   if request.method != 'POST':
       return HttpResponseBadRequest("Invalid request method")
   answer = get_object_or_404(Answer, id=request.POST.get('answer_id'))
   user = request.user
   has_downvoted = answer.downvotes.filter(id=user.id).exists()
   has_upvoted = answer.upvotes.filter(id=user.id).exists()
   if has_downvoted:
       answer.downvotes.remove(user)
   else:
       answer.downvotes.add(user)
       if has_upvoted:
           answer.upvotes.remove(user)
   if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
       return JsonResponse({
           'upvotes': answer.upvotes.count(), 'downvotes': answer.downvotes.count(),
           'user_upvoted': answer.upvotes.filter(id=user.id).exists(),
           'user_downvoted': answer.downvotes.filter(id=user.id).exists(),
       })
   else:
       redirect_url = reverse('topic-detail', kwargs={'pk': answer.user_post.pk}) + f'#answer-{answer.pk}'
       return redirect(redirect_url)

def blogListView(request):
   all_posts = BlogPost.objects.all().order_by('-timestamp')
   categories = Category.objects.annotate(num_posts=Count('posts')).order_by('name')
   context = {'all_posts': all_posts, 'categories': categories}
   return render(request, 'forum/blog-listing.html', context)

def blogDetailView(request, slug):
   post_detail = get_object_or_404(BlogPost, slug=slug)
   categories = Category.objects.annotate(num_posts=Count('posts')).order_by('name')
   context = {'post_detail': post_detail, 'categories': categories}
   return render(request, 'forum/blog-detail.html', context)

def categoryDetailView(request, category_id):
   category = get_object_or_404(Category.objects.annotate(num_posts=Count('posts')), id=category_id)
   posts_list = category.posts.select_related('author__user', 'category') \
                            .prefetch_related('answers', 'views') \
                            .order_by('-last_activity')
   paginator = Paginator(posts_list, POSTS_PER_PAGE_MAIN)
   page_number = request.GET.get('page')
   try:
       page_obj = paginator.get_page(page_number)
   except PageNotAnInteger:
       page_obj = paginator.get_page(1)
   except EmptyPage:
       page_obj = paginator.get_page(paginator.num_pages)
   categories = Category.objects.annotate(num_posts=Count('posts')).order_by('name')
   context = {
       'category': category, 'page_obj': page_obj, 'paginator': paginator,
       'categories': categories, 'active_category': category,
   }
   return render(request, 'forum/category-detail.html', context)

def category_list(request):
   categories = Category.objects.annotate(num_posts=Count('posts')).order_by('name')
   context = {'categories': categories}
   return render(request, 'forum/category-list.html', context)

@login_required(login_url='login')
def editPost(request, pk):
   post = get_object_or_404(UserPost.objects.select_related('author__user', 'category'), pk=pk)
   if not (request.user == post.author.user or request.user.is_staff):
       messages.error(request, "У вас немає прав для редагування цього поста.")
       return redirect(post.get_absolute_url())
   if request.method == 'POST':
       form = UserPostForm(request.POST, request.FILES, instance=post)
       if form.is_valid():
           form.save()
           post.update_last_activity()
           messages.success(request, "Пост успішно оновлено!")
           return redirect(post.get_absolute_url())
       else:
           messages.error(request, "Будь ласка, виправте помилки у формі.")
   else:
       form = UserPostForm(instance=post)
   context = {'form': form, 'post': post}
   return render(request, 'forum/edit-post.html', context)