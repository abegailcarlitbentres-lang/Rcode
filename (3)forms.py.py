from django import forms
from .models import Survey, Question, Choice, Answer


class SurveyForm(forms.ModelForm):
    class Meta:
        model = Survey
        fields = ['title', 'description', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Survey Title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text', 'question_type', 'required', 'order']
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control'}),
            'question_type': forms.Select(attrs={'class': 'form-select'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ['text']
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choice option'}),
        }


class DynamicSurveyForm(forms.Form):
    """Dynamically generates form fields based on survey questions."""

    def __init__(self, survey, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.survey = survey

        for question in survey.questions.all():
            field_name = f'question_{question.id}'

            if question.question_type == 'text':
                self.fields[field_name] = forms.CharField(
                    label=question.text,
                    required=question.required,
                    widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
                )

            elif question.question_type == 'radio':
                choices = [(c.id, c.text) for c in question.choices.all()]
                self.fields[field_name] = forms.ChoiceField(
                    label=question.text,
                    required=question.required,
                    choices=choices,
                    widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
                )

            elif question.question_type == 'checkbox':
                choices = [(c.id, c.text) for c in question.choices.all()]
                self.fields[field_name] = forms.MultipleChoiceField(
                    label=question.text,
                    required=question.required,
                    choices=choices,
                    widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
                )

            elif question.question_type == 'rating':
                self.fields[field_name] = forms.ChoiceField(
                    label=question.text,
                    required=question.required,
                    choices=[(str(i), str(i)) for i in range(1, 6)],
                    widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
                )