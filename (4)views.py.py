

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Count
from .models import Survey, Question, Choice, Response, Answer
from .forms import SurveyForm, QuestionForm, ChoiceForm, DynamicSurveyForm
import qrcode
import qrcode.image.svg
from io import BytesIO
from django.core.files import File
import json


# ──────────────────────────────────────────
# QR Code Generator (saves to model)
# ──────────────────────────────────────────
def generate_qr_code(survey, request):
    url = survey.get_survey_url(request)
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    filename = f'qr_{survey.unique_id}.png'
    survey.qr_code.save(filename, File(buffer), save=True)


# ──────────────────────────────────────────
# Inline QR Code (SVG — no file saved)
# ──────────────────────────────────────────
def qr_svg_view(request, unique_id):
    survey = get_object_or_404(Survey, unique_id=unique_id)
    url = survey.get_survey_url(request)

    factory = qrcode.image.svg.SvgImage
    qr = qrcode.make(url, image_factory=factory)

    buffer = BytesIO()
    qr.save(buffer)
    buffer.seek(0)

    return HttpResponse(buffer.getvalue(), content_type='image/svg+xml')


# ──────────────────────────────────────────
# Survey CRUD
# ──────────────────────────────────────────
@login_required
def dashboard(request):
    surveys = Survey.objects.filter(creator=request.user).annotate(
        response_count=Count('responses')
    )
    return render(request, 'survey/dashboard.html', {'surveys': surveys})


@login_required
def create_survey(request):
    if request.method == 'POST':
        form = SurveyForm(request.POST)
        if form.is_valid():
            survey = form.save(commit=False)
            survey.creator = request.user
            survey.save()
            generate_qr_code(survey, request)
            messages.success(request, 'Survey created! QR Code generated.')
            return redirect('survey_detail', pk=survey.pk)
    else:
        form = SurveyForm()
    return render(request, 'survey/create_survey.html', {'form': form})


@login_required
def survey_detail(request, pk):
    survey = get_object_or_404(Survey, pk=pk, creator=request.user)
    questions = survey.questions.prefetch_related('choices')
    return render(request, 'survey/survey_detail.html', {
        'survey': survey,
        'questions': questions,
    })


@login_required
def add_question(request, survey_pk):
    survey = get_object_or_404(Survey, pk=survey_pk, creator=request.user)
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.survey = survey
            question.save()

            # Save choices if provided
            choices = request.POST.getlist('choices[]')
            for choice_text in choices:
                if choice_text.strip():
                    Choice.objects.create(question=question, text=choice_text.strip())

            messages.success(request, 'Question added.')
            return redirect('survey_detail', pk=survey.pk)
    else:
        form = QuestionForm()
    return render(request, 'survey/add_question.html', {'form': form, 'survey': survey})


@login_required
def delete_question(request, pk):
    question = get_object_or_404(Question, pk=pk, survey__creator=request.user)
    survey_pk = question.survey.pk
    question.delete()
    return redirect('survey_detail', pk=survey_pk)


# ──────────────────────────────────────────
# Taking a Survey (Public)
# ──────────────────────────────────────────
def take_survey(request, unique_id):
    survey = get_object_or_404(Survey, unique_id=unique_id, is_active=True)
    form = DynamicSurveyForm(survey, request.POST or None)

    if request.method == 'POST' and form.is_valid():
        ip = request.META.get('REMOTE_ADDR')
        response = Response.objects.create(survey=survey, respondent_ip=ip)

        for question in survey.questions.all():
            field_name = f'question_{question.id}'
            answer = Answer.objects.create(response=response, question=question)

            if question.question_type == 'text':
                answer.text_answer = form.cleaned_data.get(field_name, '')
                answer.save()
            elif question.question_type in ['radio', 'rating']:
                choice_id = form.cleaned_data.get(field_name)
                if question.question_type == 'rating':
                    answer.text_answer = str(choice_id)
                    answer.save()
                else:
                    try:
                        choice = Choice.objects.get(id=choice_id)
                        answer.choice_answers.add(choice)
                    except Choice.DoesNotExist:
                        pass
            elif question.question_type == 'checkbox':
                choice_ids = form.cleaned_data.get(field_name, [])
                choices = Choice.objects.filter(id__in=choice_ids)
                answer.choice_answers.set(choices)

        return redirect('survey_thankyou')

    return render(request, 'survey/take_survey.html', {'survey': survey, 'form': form})


def survey_thankyou(request):
    return render(request, 'survey/thankyou.html')


# ──────────────────────────────────────────
# Results
# ──────────────────────────────────────────
@login_required
def survey_results(request, pk):
    survey = get_object_or_404(Survey, pk=pk, creator=request.user)
    questions = survey.questions.prefetch_related('choices', 'answer_set__choice_answers')
    results = []

    for question in questions:
        data = {'question': question, 'answers': []}

        if question.question_type == 'text':
            data['answers'] = Answer.objects.filter(
                question=question
            ).values_list('text_answer', flat=True)

        elif question.question_type in ['radio', 'checkbox']:
            choice_data = []
            for choice in question.choices.all():
                count = Answer.objects.filter(
                    question=question,
                    choice_answers=choice
                ).count()
                choice_data.append({'choice': choice.text, 'count': count})
            data['choice_data'] = choice_data
            data['chart_data'] = json.dumps({
                'labels': [c['choice'] for c in choice_data],
                'counts': [c['count'] for c in choice_data],
            })

        elif question.question_type == 'rating':
            rating_data = []
            for i in range(1, 6):
                count = Answer.objects.filter(
                    question=question, text_answer=str(i)
                ).count()
                rating_data.append({'rating': i, 'count': count})
            data['rating_data'] = rating_data

        results.append(data)

    return render(request, 'survey/results.html', {
        'survey': survey,
        'results': results,
        'total_responses': survey.responses.count(),
    })
