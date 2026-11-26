

from django import forms

from .models import UserPost, Answer, Category


class UserPostForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        empty_label="-- Виберіть категорію --",
        widget=forms.Select(attrs={
            'class': 'form-control form-control-style-3' 
            }),
        required=True,
        label="Категорія"
    )

    title = forms.CharField(
        label="Заголовок",
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-style-3', 
            'placeholder': 'Введіть заголовок теми...',
        }),
        max_length=200
    )

    description = forms.CharField(
        label="Опис",
        widget=forms.Textarea(attrs={
            'class': 'form-control form-control-style-3', 
            'placeholder': 'Опишіть ваше питання або тему детально...',
            'rows': 8,
        }),
        max_length=1000 
    )

    image = forms.ImageField(
        label="Зображення до теми (необов'язково)",
        required=False,
        widget=forms.ClearableFileInput(attrs={
            
            'class': 'block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none file:mr-4 file:py-2 file:px-4 file:rounded-l-lg file:border-0 file:text-sm file:font-semibold file:bg-yellow-50 file:text-yellow-700 hover:file:bg-yellow-100 form-control-style-3-file' 
            
        }),
        help_text="Макс. розмір: 2MB. Формати: JPG, PNG, GIF."
    )

    class Meta:
        model = UserPost
        fields = ['category', 'title', 'description', 'image']


class AnswerForm(forms.ModelForm):
    content = forms.CharField(
        label="", 
        widget=forms.Textarea(attrs={
            'class':'form-control form-control-style-3', 
            'placeholder':'Напишіть вашу відповідь тут...',
            'rows': 4,
            'required': True, 
        }),
        max_length=1000 
    )

    image = forms.ImageField(
        label="Прикріпити зображення (необов'язково)",
        required=False,
        widget=forms.ClearableFileInput(attrs={
            
            'class': 'block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none file:mr-4 file:py-2 file:px-4 file:rounded-l-lg file:border-0 file:text-sm file:font-semibold file:bg-yellow-50 file:text-yellow-700 hover:file:bg-yellow-100 mt-2 form-control-style-3-file'
            
        }),
        help_text="Макс. розмір: 2MB. Формати: JPG, PNG, GIF."
    )

    class Meta:
        model = Answer
        fields = ['content', 'image']