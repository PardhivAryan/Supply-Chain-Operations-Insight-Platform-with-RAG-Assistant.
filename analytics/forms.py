from django import forms


class ProcessDatasetForm(forms.Form):
    pass


class DatasetUploadForm(forms.Form):
    zip_file = forms.FileField(
        label="Upload supply-chain dataset ZIP",
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control",
                "accept": ".zip,application/zip,application/x-zip-compressed",
            }
        ),
    )

    def clean_zip_file(self):
        zip_file = self.cleaned_data["zip_file"]
        if not zip_file.name.lower().endswith(".zip"):
            raise forms.ValidationError("Please upload a .zip file.")
        return zip_file


class ChatQuestionForm(forms.Form):
    question = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "Ask a question about generated supply-chain reports...",
                "class": "form-control",
            }
        )
    )
