from django.template import Library

register = Library()

@register.filter
def get_range( value ):
  """
    Filter - returns a list containing range made from given value
    Usage (in template):

    <ul>{% for i in 3|get_range %}
      <li>{{ i }}. Do something</li>
    {% endfor %}</ul>

    Results with the HTML:
    <ul>
      <li>0. Do something</li>
      <li>1. Do something</li>
      <li>2. Do something</li>
    </ul>

    Instead of 3 one may use the variable set in the views
  """
  return range( value )

@register.filter
def first_author( full_author_list ):
  split_authors = full_author_list.split(', ')
  first_author=split_authors[0].replace("'", "").replace("[","")
  last_name = first_author.split(' ')[0]

  if len(split_authors) is 1:
      return last_name
  else:
      return last_name + ' et al'

@register.filter
def parse_full_names( full_names ):
  split_full_names = full_names.split("'")
  num_full_names = int((len(split_full_names)-1)/2)
  rn = ""
  for i in range(num_full_names):
      singleName = split_full_names[2*i+1]
      formattedSingleName = singleName.split(", ")[1] + " " + singleName.split(", ")[0]
      if i is 0:
          rn = formattedSingleName
      elif i is num_full_names-1:
          rn = rn + " & " + formattedSingleName
      else:
          rn = rn + ", " + formattedSingleName
  return rn

@register.filter
def citation_year( full_date ):
  return full_date.split(' ')[0]

@register.filter
def increment( i ):
  return i+1

@register.filter
def decrement( i ):
  return i-1
