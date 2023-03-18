from django import forms
from django.core.exceptions import ValidationError

from lists.models import Item

EMPTY_ITEM_ERROR = "You can't have an empty list item"
DUPLICATE_ITEM_ERROR = "You've already got this in your list"

# Use this form for new lists because duplicates are impossible.
class ItemForm(forms.models.ModelForm):

    def save(self, for_list):
        self.instance.list = for_list
        return super().save()

    class Meta:
        model = Item
        fields = ('text',)
        widgets = {'text': forms.fields.TextInput(
                            attrs={'placeholder': 'Enter a to-do item',
                                   'class': 'form-control input-lg'}
                        )
        }
        error_messages = {'text': {'required': EMPTY_ITEM_ERROR}}

# Duplicates can only happen with existings lists.
class ExistingListItemForm(ItemForm):

    # We add the for_list argument to the constructor.
    def __init__(self, for_list, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.list = for_list
    
    def save(self):
        return forms.models.ModelForm.save(self)
    
    # This is called whenever we use the method form.is_valid()
    def validate_unique(self):
        try:
            self.instance.validate_unique()
        except ValidationError as e:
            e.error_dict = {'text': [DUPLICATE_ITEM_ERROR]}
            self._update_errors(e)

