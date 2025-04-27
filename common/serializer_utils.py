def error_formatter(error):

    was_not_list = False

    if not isinstance(error, list):
        error = [error]
        was_not_list = True

    res = ""
    count = 1

    for el in error:
        temp_res = ""
        for key, value in el.items():
            if was_not_list:
                temp_res = temp_res + f"{value[0]} \n"
                continue
            temp_res = temp_res + f"{count}. {key} = {value[0]} \n"
        count += 1
        res = res + temp_res

    return res

def get_serialized_or_none(serializer_class, instance):
    if instance:
        return serializer_class(instance).data
    return None

def update_nested_objects(model_class, nested_data_list, extra_fields=None):
    """
    Utility function to handle updating/creating nested objects with optional extra fields.
    
    Args:
        model_class: The Django model class to update/create instances for
        nested_data_list: List of dictionaries containing the data for nested objects
        extra_fields: Optional dict of field names and values to add (e.g., {'organization': instance})
    
    Returns:
        None
    """
    for item_data in nested_data_list:
        if not isinstance(item_data, dict):
            continue
            
        # Add extra fields if provided
        if extra_fields and isinstance(extra_fields, dict):
            item_data.update(extra_fields)
            
        if "id" in item_data:
            item_id = item_data.pop('id')
            model_class.objects.update_or_create(
                id=item_id,
                defaults=item_data
            )
        else:
            model_class.objects.create(**item_data)
