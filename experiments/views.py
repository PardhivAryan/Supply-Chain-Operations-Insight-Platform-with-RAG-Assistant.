import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ExperimentForm, ExperimentResponseForm
from django.views.decorators.http import require_POST

from .models import Experiment, ExperimentResponse


@login_required
def experiment_list(request):
    experiments = Experiment.objects.annotate(response_count=Count("responses"))
    return render(request, "experiments/experiment_list.html", {"experiments": experiments})


@login_required
def experiment_create(request):
    form = ExperimentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        experiment = form.save()
        messages.success(request, "Experiment created.")
        return redirect("experiments:experiment_detail", pk=experiment.pk)
    return render(request, "experiments/experiment_form.html", {"form": form})


@login_required
def experiment_detail(request, pk):
    experiment = get_object_or_404(Experiment, pk=pk)
    form = ExperimentResponseForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        response = form.save(commit=False)
        response.experiment = experiment
        response.save()
        messages.success(request, "Participant response added.")
        return redirect("experiments:experiment_detail", pk=experiment.pk)

    responses = experiment.responses.all()
    summary = responses.values("assigned_condition").annotate(
        response_count=Count("id"),
        average_confidence=Avg("confidence_score"),
        average_response_time=Avg("response_time_seconds"),
    )
    return render(
        request,
        "experiments/experiment_detail.html",
        {
            "experiment": experiment,
            "responses": responses,
            "response_form": form,
            "summary": summary,
        },
    )


@login_required
def export_responses_csv(request, pk):
    experiment = get_object_or_404(Experiment, pk=pk)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="experiment_{experiment.pk}_responses.csv"'
    writer = csv.writer(response)
    writer.writerow(
        [
            "participant_code",
            "assigned_condition",
            "decision",
            "confidence_score",
            "response_time_seconds",
            "notes",
            "created_at",
        ]
    )
    for item in experiment.responses.all().order_by("created_at"):
        writer.writerow(
            [
                item.participant_code,
                item.assigned_condition,
                item.decision,
                item.confidence_score,
                item.response_time_seconds,
                item.notes,
                item.created_at,
            ]
        )
    return response


@login_required
@require_POST
def delete_experiment_response(request, pk, response_id):
    experiment = get_object_or_404(Experiment, pk=pk)
    response = get_object_or_404(ExperimentResponse, pk=response_id, experiment=experiment)
    participant_code = response.participant_code
    response.delete()
    messages.success(request, f"Participant response {participant_code} deleted.")
    return redirect("experiments:experiment_detail", pk=experiment.pk)
