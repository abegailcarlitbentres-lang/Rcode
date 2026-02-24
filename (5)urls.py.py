
from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('create/', views.create_survey, name='create_survey'),
    path('survey/<int:pk>/', views.survey_detail, name='survey_detail'),
    path('survey/<int:pk>/add-question/', views.add_question, name='add_question'),
    path('question/<int:pk>/delete/', views.delete_question, name='delete_question'),
    path('survey/<int:pk>/results/', views.survey_results, name='survey_results'),
    path('take/<uuid:unique_id>/', views.take_survey, name='take_survey'),
    path('qr/<uuid:unique_id>.svg', views.qr_svg_view, name='qr_svg'),
    path('thankyou/', views.survey_thankyou, name='survey_thankyou'),
]

survey_detail.html

{% extends 'base.html' %}
{% block content %}
<div class="container mt-4">
    <h2>{{ survey.title }}</h2>
    <p>{{ survey.description }}</p>

    <!-- QR Code Section -->
    <div class="card mb-4">
        <div class="card-body text-center">
            <h5>Share this Survey via QR Code</h5>
            <!-- SVG inline QR (no file storage needed) -->
            <img src="{% url 'qr_svg' survey.unique_id %}" width="200" height="200" alt="QR Code">
            <p class="mt-2 text-muted">
                Survey URL: <a href="{% url 'take_survey' survey.unique_id %}">{{ request.build_absolute_uri }}</a>
            </p>
            <!-- Download PNG QR if saved -->
            {% if survey.qr_code %}
                <a href="{{ survey.qr_code.url }}" class="btn btn-outline-primary btn-sm" download>
                    Download QR Code (PNG)
                </a>
            {% endif %}
        </div>
    </div>

    <!-- Questions List -->
    <h4>Questions ({{ questions.count }})</h4>
    {% for question in questions %}
        <div class="card mb-2">
            <div class="card-body">
                <strong>{{ forloop.counter }}. {{ question.text }}</strong>
                <span class="badge bg-secondary ms-2">{{ question.get_question_type_display }}</span>
                {% if question.choices.exists %}
                    <ul class="mt-2">
                        {% for choice in question.choices.all %}
                            <li>{{ choice.text }}</li>
                        {% endfor %}
                    </ul>
                {% endif %}
                <a href="{% url 'delete_question' question.pk %}"
                   class="btn btn-sm btn-danger float-end"
                   onclick="return confirm('Delete this question?')">Delete</a>
            </div>
        </div>
    {% empty %}
        <p class="text-muted">No questions yet.</p>
    {% endfor %}

    <a href="{% url 'add_question' survey.pk %}" class="btn btn-success">+ Add Question</a>
    <a href="{% url 'survey_results' survey.pk %}" class="btn btn-info">View Results</a>
</div>
{% endblock %}

take_survey.html
{% extends 'base.html' %}
{% block content %}
<div class="container mt-4">
    <h2>{{ survey.title }}</h2>
    <p>{{ survey.description }}</p>

    <form method="POST">
        {% csrf_token %}
        {% for field in form %}
            <div class="mb-4">
                <label class="form-label fw-bold">{{ field.label }}</label>
                {{ field }}
                {% if field.errors %}
                    <div class="text-danger">{{ field.errors }}</div>
                {% endif %}
            </div>
        {% endfor %}
        <button type="submit" class="btn btn-primary">Submit Survey</button>
    </form>
</div>
{% endblock %}


results.html

{% extends 'base.html' %}
{% block content %}
<div class="container mt-4">
    <h2>Results: {{ survey.title }}</h2>
    <p class="text-muted">Total Responses: <strong>{{ total_responses }}</strong></p>

    {% for item in results %}
        <div class="card mb-4">
            <div class="card-body">
                <h5>{{ forloop.counter }}. {{ item.question.text }}</h5>

                {% if item.question.question_type == 'text' %}
                    {% for answer in item.answers %}
                        <div class="p-2 mb-1 bg-light rounded">{{ answer }}</div>
                    {% empty %}
                        <p class="text-muted">No answers yet.</p>
                    {% endfor %}

                {% elif item.choice_data %}
                    <canvas id="chart_{{ item.question.id }}" height="100"></canvas>
                    <script>
                        const data_{{ item.question.id }} = {{ item.chart_data|safe }};
                        new Chart(document.getElementById('chart_{{ item.question.id }}'), {
                            type: 'bar',
                            data: {
                                labels: data_{{ item.question.id }}.labels,
                                datasets: [{
                                    label: 'Responses',
                                    data: data_{{ item.question.id }}.counts,
                                    backgroundColor: 'rgba(54, 162, 235, 0.6)',
                                }]
                            }
                        });
                    </script>

                {% elif item.rating_data %}
                    {% for r in item.rating_data %}
                        <div class="d-flex align-items-center mb-1">
                            <span class="me-2">⭐ {{ r.rating }}</span>
                            <div class="progress flex-grow-1" style="height:20px;">
                                <div class="progress-bar" style="width: {% if total_responses %}{{ r.count|floatformat:0 }}{% else %}0{% endif %}%">
                                    {{ r.count }}
                                </div>
                            </div>
                        </div>
                    {% endfor %}
                {% endif %}
            </div>
        </div>
    {% endfor %}
</div>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
{% endblock %}
