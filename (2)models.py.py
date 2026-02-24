from django.db import models
from django.contrib.auth.models import User
import uuid

class Survey(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    unique_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    qr_code = models.ImageField(upload_to='qrcodes/', blank=True, null=True)

    def __str__(self):
        return self.title

    def get_survey_url(self, request):
        return request.build_absolute_uri(f'/survey/take/{self.unique_id}/')


class Question(models.Model):
    QUESTION_TYPES = [
        ('text', 'Text'),
        ('radio', 'Multiple Choice (Single)'),
        ('checkbox', 'Multiple Choice (Multiple)'),
        ('rating', 'Rating (1-5)'),
    ]
    survey = models.ForeignKey(Survey, related_name='questions', on_delete=models.CASCADE)
    text = models.CharField(max_length=500)
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='text')
    order = models.PositiveIntegerField(default=0)
    required = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.text


class Choice(models.Model):
    question = models.ForeignKey(Question, related_name='choices', on_delete=models.CASCADE)
    text = models.CharField(max_length=255)

    def __str__(self):
        return self.text


class Response(models.Model):
    survey = models.ForeignKey(Survey, related_name='responses', on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(auto_now_add=True)
    respondent_ip = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self):
        return f"Response to {self.survey.title} at {self.submitted_at}"


class Answer(models.Model):
    response = models.ForeignKey(Response, related_name='answers', on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    text_answer = models.TextField(blank=True)
    choice_answers = models.ManyToManyField(Choice, blank=True)

    def __str__(self):
        return f"Answer to {self.question.text}"