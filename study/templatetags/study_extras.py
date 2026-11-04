from django import template

register = template.Library()


@register.filter
def getitem(d, key):
    try:
        return d.get(key, "")
    except AttributeError:
        return ""


@register.filter
def seq(start_end):
    """'1,7' -> [1..7] as strings."""
    a, b = (int(x) for x in str(start_end).split(","))
    return [str(i) for i in range(a, b + 1)]
