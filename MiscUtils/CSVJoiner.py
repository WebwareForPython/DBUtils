import types


def joinCSVFields(fields):
	"""
	Returns a CSV record (eg a string) from a sequence of fields.
	Fields containing commands (,) or double quotes (") are quoted
	and double quotes are escaped (""). The terminating newline is
	NOT included.
	"""
	newFields = []
	for field in fields:
		assert type(field) is types.StringType
		if field.find('"') != -1:
			newField = '"' + field.replace('"', '""') + '"'
		elif field.find(',') != -1 or field.find('\n') != -1 or field.find('\r') != -1:
			newField = '"' + field + '"'
		else:
			newField = field
		newFields.append(newField)
	return ','.join(newFields)
