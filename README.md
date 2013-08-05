Quickbase-Python-SDK
===================

Python bindings for the QuickBase API

QBConn variables:

	error: the numerical error code returned by an API call. 0 is no error, negative values are internal to this library
	tables: a dictionary containing tablename:tableID pairs
	
QBConn(QB_URL,QB_APPID[,QB_TOKEN, QB_REALM]):

	Makes a connection to the QuickBase specified by QB_URL and QB_APPID. Uses QB_TOKEN and QB_REALM if specified.
	Note: QB_URL should have a trailing slash. ex. "https://intuitcorp.quickbase.com/db/";
	
authenticate(username,password):

	Authenticates username and password with QuickBase and stores the returned ticket. The tables variable is populated on success
	
request(params,url_ext):

	Takes a dict of param:value pairs, adds ticket, token, and realm (if specified) and makes an API call to the base URL+url_extension
	
addRecord(tableID,data):

	Adds a record with data specified by the data dict of fieldname:value pairs to tableID
	
editRecord(tableID,rid,newdata[,options]):

	Updates a record (rid) in table (tableID) with the data given by newdata fieldname:value pairs
	
deleteRecord(tableID,rid):

	Deletes record specified by rid from table specified by tableID
	
purgeRecords(tableID,query):

	Deletes records from tableID that match the QuickBase-style query
	
getFields(tableID):

	Returns a dict containing the fields of a table as fieldname:fieldID pairs
	
_getTables():

	Returns a dict containing a QuickBase app's tables as tablename:tableID pairs. This is run automatically after a successful authenticate call
	
query(tableID,query):

	Returns a list of dicts containing fieldname:value pairs that represent rows returned by the query. record ID will always be specified by the "rid" key

sql(querystr):
	Performs a query() after translating a simple SQL-style string to QuickBase's query format
	
	Example: qb.sql("SELECT * FROM users WHERE name\`EX\`John\_Doe OR role\`EX\`fakeperson") #The \_ represents a space. This is a very basic function that doesn't use state machines. Note: field and table names will not have spaces
	Example: qb.sql("SELECT firstname|lastname FROM users WHERE paid\`EX\`true ORDER BY lastname ASC LIMIT 100")
	Example: qb.sql("DELETE FROM assets WHERE value\`BF\`0")
	Please contribute any improvents you make on this function back to this repo. It would make life so much easier for all QuickBase+Python users :)
