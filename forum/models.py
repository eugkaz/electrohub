from django.db import models
from django.urls import reverse
from django.utils import timezone


from django.contrib.auth.models import User



class Author(models.Model):
   user = models.OneToOneField(User, on_delete = models.CASCADE)

   is_doctor = models.BooleanField(default=False)

   def __str__(self):
       return self.user.username

class Category(models.Model):
   name = models.CharField(max_length=100, unique=True)
   description = models.TextField(blank=True, null=True)
   created_at = models.DateTimeField(auto_now_add=True)

   class Meta:
       verbose_name_plural = "Categories" 

   def __str__(self):
       return self.name

class UserPost(models.Model):
   author = models.ForeignKey(Author, on_delete=models.CASCADE, null=True, related_name='user_posts')
   category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='posts')
   title = models.CharField(max_length=200, null=True)
   description = models.TextField(max_length=1000, null=True)
   image = models.ImageField(upload_to='forum_posts/', null=True, blank=True, verbose_name="Зображення до теми")
   date_created = models.DateTimeField(auto_now_add=True, null=True)
   last_activity = models.DateTimeField(auto_now_add=True, null=True)

   class Meta:
       ordering = ['-last_activity']

   def __str__(self):
       return self.title if self.title else "Без назви"

   def get_absolute_url(self):
       return reverse('topic-detail', kwargs={'pk': self.pk})

   @property
   def answer_count(self):
       return self.answers.count()

   @property
   def topic_view_count(self):
       return self.views.count()

   def update_last_activity(self):
       self.last_activity = timezone.now()
       self.save(update_fields=['last_activity'])

   def get_last_reply(self):
       return self.answers.order_by('-date_created').first()


class Answer(models.Model):
   user_post = models.ForeignKey(UserPost, on_delete=models.CASCADE, related_name='answers')
   user = models.ForeignKey(User, on_delete = models.CASCADE, related_name='forum_answers')
   content = models.TextField(max_length=1000)
   image = models.ImageField(upload_to='forum_answers/', null=True, blank=True, verbose_name="Зображення до відповіді")
   date_created = models.DateTimeField(auto_now_add=True, null=True)
   date_modified = models.DateTimeField(auto_now=True)
   upvotes = models.ManyToManyField(User, blank=True, related_name='upvoted_answers')
   downvotes = models.ManyToManyField(User, blank=True, related_name='downvoted_answers')
   parent = models.ForeignKey(
       'self',
       on_delete=models.CASCADE,
       null=True,
       blank=True,
       related_name='replies'
   )

   class Meta:
       ordering = ['date_created']

   def __str__(self):
       if self.parent:
           return f"Reply by {self.user.username} to comment {self.parent.id} on '{self.user_post.title}'"
       return f"Answer by {self.user.username} on '{self.user_post.title}'"

   @property
   def upvotes_count(self):
       return self.upvotes.count()

   @property
   def downvotes_count(self):
       return self.downvotes.count()

   @property
   def is_edited(self):
       return self.date_modified > self.date_created + timezone.timedelta(minutes=1)

   def save(self, *args, **kwargs):
       is_new = self._state.adding
       super().save(*args, **kwargs)
       if is_new and not self.parent:
            self.user_post.update_last_activity()


class BlogPost(models.Model):
   title = models.CharField(max_length=100)
   slug = models.SlugField(max_length=200, unique=True, null=True, blank=True)
   content = models.TextField(blank=True, null=True)
   timestamp = models.DateTimeField(auto_now_add=True)
   thumbnail = models.ImageField(default="header.jpg", null=True, blank=True)

   def __str__(self):
       return self.title

class PostView(models.Model):
   user_post = models.ForeignKey(UserPost, on_delete=models.CASCADE, related_name='views')
   user = models.ForeignKey(User, on_delete = models.CASCADE)
   timestamp = models.DateTimeField(auto_now_add=True)

   class Meta:
       unique_together = ('user_post', 'user')

   def __str__(self):
       return f"{self.user.username} viewed '{self.user_post.title}'"