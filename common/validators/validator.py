class Validator:
    # main header file for all manifest validator types
    PREFIX_4_NEW_FIELD = "new#"
    def __init__(self, profile_id, fields, data, errors, warnings, flag, **kwargs):
        self.profile_id = profile_id
        self.fields = fields
        self.data = data
        self.errors = errors
        self.warnings = warnings
        self.flag = flag
        self.kwargs = kwargs

    def validate(self):
        raise NotImplemented
