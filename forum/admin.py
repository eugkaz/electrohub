

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe 
from .models import Category, UserPost, Author, Answer, PostView, BlogPost


admin.site.site_header = "ElectroHub Forum Admin"
admin.site.site_title = "ElectroHub Admin Portal"
admin.site.index_title = "Welcome to ElectroHub Forum Administration"


class AnswerInline(admin.TabularInline): 
    model = Answer
    fields = ('user', 'content_preview', 'parent_link', 'date_created', 'is_edited') 
    readonly_fields = ('content_preview', 'parent_link', 'date_created', 'is_edited') 
    extra = 0 
    show_change_link = True 
    ordering = ('date_created',) 
    raw_id_fields = ('user', 'parent') 

    def content_preview(self, obj):
        
        return obj.content[:80] + '...' if len(obj.content) > 80 else obj.content
    content_preview.short_description = 'Відповідь (початок)'

    def parent_link(self, obj):
        
        if obj.parent:
            link = reverse("admin:forum_answer_change", args=[obj.parent.id])
            return format_html('<a href="{}">Відповідь #{}</a>', link, obj.parent.id)
        return "-"
    parent_link.short_description = 'Відповідь на'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'post_count', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at',)

    def post_count(self, obj):
        
        return obj.posts.count()
    post_count.short_description = 'К-ть тем' 


@admin.register(UserPost)
class UserPostAdmin(admin.ModelAdmin):
    list_display = ('title_link', 'author_link', 'category', 'answer_count_display', 'view_count_display', 'last_activity', 'date_created')
    list_filter = ('category', 'date_created', 'last_activity', 'author') 
    search_fields = ('title', 'description', 'author__user__username', 'category__name') 
    readonly_fields = ('date_created', 'last_activity', 'answer_count_display', 'view_count_display') 
    date_hierarchy = 'last_activity' 
    ordering = ('-last_activity',) 
    raw_id_fields = ('author', 'category') 
    list_per_page = 25 
    inlines = [AnswerInline] 

    def title_link(self, obj):
        
        
        try:
            url = obj.get_absolute_url()
            return format_html('<a href="{}" target="_blank">{}</a>', url, obj.title)
        except: 
             admin_url = reverse("admin:forum_userpost_change", args=[obj.pk])
             return format_html('<a href="{}">{}</a>', admin_url, obj.title)
    title_link.short_description = 'Заголовок'
    title_link.admin_order_field = 'title' 

    def author_link(self, obj):
        
        if obj.author:
            link = reverse("admin:forum_author_change", args=[obj.author.id])
            return format_html('<a href="{}">{}</a>', link, obj.author.user.username)
        return "-"
    author_link.short_description = 'Автор'
    author_link.admin_order_field = 'author__user__username'

    def answer_count_display(self, obj):
        
        return obj.answer_count
    answer_count_display.short_description = 'Відп.'
    answer_count_display.admin_order_field = 'answers' 

    def view_count_display(self, obj):
         
        return obj.topic_view_count 
    view_count_display.short_description = 'Перегл.'
    view_count_display.admin_order_field = 'views' 

    
    
    
    
    
    
    
    

    
    
    
    

    
    
    
    


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('user_link', 'get_full_name', 'get_email', 'post_count', 'answer_count', 'is_doctor')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email')
    list_filter = ('is_doctor',)
    readonly_fields = ('post_count', 'answer_count') 
    raw_id_fields = ('user',) 

    def user_link(self, obj):
        link = reverse("admin:auth_user_change", args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', link, obj.user.username)
    user_link.short_description = 'Користувач (Login)'

    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = "Повне ім'я"

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'

    def post_count(self, obj):
        
        return obj.user_posts.count()
    post_count.short_description = 'К-ть тем'

    def answer_count(self, obj):
         
        return obj.user.forum_answers.count() 
    answer_count.short_description = 'К-ть відповідей'


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('short_content', 'user_link', 'user_post_link', 'parent_info', 'date_created', 'is_edited_display')
    list_filter = ('date_created', ('parent', admin.EmptyFieldListFilter), 'user', 'user_post__category', 'user_post') 
    search_fields = ('content', 'user__username', 'user_post__title')
    readonly_fields = ('date_created', 'date_modified', 'parent_link') 
    date_hierarchy = 'date_created'
    raw_id_fields = ('user', 'user_post', 'parent') 
    list_per_page = 30
    ordering = ('-date_created',)

    fieldsets = ( 
        (None, {
            'fields': ('user', 'user_post', 'parent_link', 'parent') 
        }),
        ('Вміст відповіді', {
            'fields': ('content',)
        }),
        ('Голоси (Інформаційно)', {
            'fields': ('get_upvotes', 'get_downvotes'), 
             'classes': ('collapse',), 
        }),
         ('Дати', {
            'fields': ('date_created', 'date_modified'),
             'classes': ('collapse',), 
        }),
    )

    def short_content(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    short_content.short_description = 'Вміст'

    def user_link(self, obj):
        link = reverse("admin:auth_user_change", args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', link, obj.user.username)
    user_link.short_description = 'Користувач'
    user_link.admin_order_field = 'user__username'

    def user_post_link(self, obj):
        link = reverse("admin:forum_userpost_change", args=[obj.user_post.id])
        
        title = obj.user_post.title[:30] + '...' if len(obj.user_post.title) > 30 else obj.user_post.title
        return format_html('<a href="{}">{}</a>', link, title)
    user_post_link.short_description = 'Тема'
    user_post_link.admin_order_field = 'user_post__title'

    def parent_info(self, obj):
        if obj.parent:
            link = reverse("admin:forum_answer_change", args=[obj.parent.id])
            return format_html('На <a href="{}">відп. #{}</a> (від {})', link, obj.parent.id, obj.parent.user.username)
        return "Верхній рівень"
    parent_info.short_description = 'Відповідь на'
    

    def parent_link(self, obj):
         
         if obj.parent:
             link = reverse("admin:forum_answer_change", args=[obj.parent.id])
             return format_html('<a href="{}" target="_blank">Переглянути батьківську відповідь #{}</a>', link, obj.parent.id)
         return "Немає (відповідь на пост)"
    parent_link.short_description = 'Батьківська відповідь'

    def is_edited_display(self, obj):
        return obj.is_edited 
    is_edited_display.short_description = 'Редаг.'
    is_edited_display.boolean = True 

    def get_upvotes(self, obj):
        
        users = ", ".join([u.username for u in obj.upvotes.all()[:5]]) 
        count = obj.upvotes.count()
        if count > 5:
            users += f" ... та ще {count - 5}"
        return f"{count}: {users}" if count > 0 else "0"
    get_upvotes.short_description = 'Лайки'

    def get_downvotes(self, obj):
        users = ", ".join([u.username for u in obj.downvotes.all()[:5]])
        count = obj.downvotes.count()
        if count > 5:
            users += f" ... та ще {count - 5}"
        return f"{count}: {users}" if count > 0 else "0"
    get_downvotes.short_description = 'Дизлайки'


@admin.register(PostView) 
class PostViewAdmin(admin.ModelAdmin):
    list_display = ('user_post_link', 'user_link', 'timestamp')
    list_filter = ('timestamp', 'user_post__category', 'user')
    search_fields = ('user__username', 'user_post__title')
    readonly_fields = ('timestamp', 'user', 'user_post') 
    date_hierarchy = 'timestamp'
    list_per_page = 50
    ordering = ('-timestamp',)

    def user_post_link(self, obj):
        link = reverse("admin:forum_userpost_change", args=[obj.user_post.id])
        title = obj.user_post.title[:40] + '...' if len(obj.user_post.title) > 40 else obj.user_post.title
        return format_html('<a href="{}">{}</a>', link, title)
    user_post_link.short_description = 'Тема'

    def user_link(self, obj):
        link = reverse("admin:auth_user_change", args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', link, obj.user.username)
    user_link.short_description = 'Користувач'

    
    def has_add_permission(self, request, obj=None):
        return False
    
    
    


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'timestamp', 'thumbnail_preview')
    search_fields = ('title', 'content', 'slug')
    prepopulated_fields = {'slug': ('title',)} 
    readonly_fields = ('timestamp', 'thumbnail_preview',)
    list_filter = ('timestamp',)
    ordering = ('-timestamp',)

    def thumbnail_preview(self, obj):
        
        if obj.thumbnail:
             
            return format_html('<img src="{}" style="max-height: 50px; max-width: 100px;" />', obj.thumbnail.url)
        return "(Немає зображення)"
    thumbnail_preview.short_description = 'Мініатюра'


