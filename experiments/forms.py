from django import forms

from .models import Experiment, ExperimentResponse


class ExperimentForm(forms.ModelForm):
    class Meta:
        model = Experiment
        fields = [
            "title",
            "research_question",
            "control_condition",
            "treatment_condition",
            "status",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "research_question": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "control_condition": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "treatment_condition": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }


class ExperimentResponseForm(forms.ModelForm):
    class Meta:
        model = ExperimentResponse
        fields = [
            "participant_code",
            "assigned_condition",
            "decision",
            "confidence_score",
            "response_time_seconds",
            "notes",
        ]
        widgets = {
            "participant_code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter participant ID",
                }
            ),
            "assigned_condition": forms.Select(attrs={"class": "form-select"}),
            "decision": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "confidence_score": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "max": "100",
                    "step": "0.01",
                    "placeholder": "Enter confidence score",
                }
            ),
            "response_time_seconds": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                    "placeholder": "Enter response time",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Add relevant study observations",
                }
            ),
        }
        labels = {
            "participant_code": "Participant code",
            "assigned_condition": "Assigned condition",
            "decision": "Decision made by participant",
            "confidence_score": "Confidence score (0-100)",
            "response_time_seconds": "Response time in seconds",
            "notes": "Notes",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        condition_choices = [
            choice for choice in self.fields["assigned_condition"].choices if choice[0]
        ]
        self.fields["assigned_condition"].choices = [("", "Select condition")] + condition_choices
        self.fields["decision"].widget.attrs[
            "placeholder"
        ] = "Summarize the participant decision"
        self.fields["participant_code"].help_text = "Use a simple anonymous ID for each participant."
        self.fields["assigned_condition"].help_text = "CONTROL = raw records only. TREATMENT = dashboard, report, and assistant."
        self.fields["decision"].help_text = "Write the business decision the participant made after reviewing the assigned material."
        self.fields["confidence_score"].help_text = "Enter how confident the participant was, from 0 to 100."
        self.fields["response_time_seconds"].help_text = "Enter how many seconds the participant took to decide."
