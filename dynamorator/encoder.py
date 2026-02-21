from json import JSONEncoder
from datetime import datetime, date


class DateTimeEncoder(JSONEncoder):
    """JSON encoder that handles datetime objects by converting them to ISO format strings."""
    
    def default(self, o):
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        return super().default(o)
