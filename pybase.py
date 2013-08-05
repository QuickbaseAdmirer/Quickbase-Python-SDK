#!/usr/bin/python

#import urllib.request, urllib.parse, urllib.error #Use this for Python > 3
import urllib		#Use this line instead of the previous for Python < 3.0
import xml.etree.ElementTree as elementree
import re
import string

class QBConn:
	def __init__(self,url,appid,token=None,realm=""):
		self.url = url
		self.token = token
		self.appid = appid
		self.ticket = None
		self.realm = realm	#This allows one QuickBase realm to proxy for another
		self.error = 0		#Set after every API call. A non-zero value indicates an error. A negative value indicates an error with this library
		self.tables = {}

	def authenticate(self,username,password):
		params = {'act':'API_Authenticate','username':username,'password':password}
		resp = self.request(params,'main')
		if self.error != 0:
			return
		else:
			self.ticket = resp.find("ticket").text
			self.tables = self._getTables()

	#Adds the appropriate fields to the request and sends it to QB
	#Takes a dict of parameter:value pairs and the url extension (main or your table ID, mostly)
	def request(self,params,url_ext):
		url = self.url
		url += url_ext
		params['ticket'] = self.ticket
		params['apptoken'] = self.token
		params['realmhost'] = self.realm
		#urlparams = urllib.parse.urlencode(params) #Use this line for Python > 3
		urlparams = urllib.urlencode(params)	#use this line for < Python 3
		#resp = urllib.request.FancyURLopener().open(url+"?"+urlparams).read() #Use this line for Python > 3
		resp = urllib.FancyURLopener().open(url+"?"+urlparams).read() #use this line for < Python 3
		if re.match('^\<\?xml version=',resp.decode("utf-8")) == None:
			print("No useful data received")
			self.error = -1		#No XML data returned
		else:
			tree = elementree.fromstring(resp)
			self.error = int(tree.find('errcode').text)
			return tree

	#Creates a record with the given data in the table specified by tableID
	#Takes a tableID (you can get this using qb.tables["yourtable"])
	#Also takes a dict containing field name:field value pairs
	def addRecord(self,tableID,data):
		fields = self.getFields(tableID)
		params = {'act':'API_AddRecord'}
		for field in data:
				if field in fields:
					params["_fid_"+fields[field]] = data[field]
		return self.request(params,tableID)

	#Updates a reord with the given data
	#Takes the record's table ID, record ID, a dict containing field:newvalue pairs, and an optional dict with param:value pairs
	def editRecord(self,tableID,rid,newdata,options={}):
		params = {'act':'API_EditRecord','rid':rid}
		fields = self.getFields(tableID)
		for key,value in list(newdata.items()):
			if key.isdigit():
				params["_fid_"+key] = value
			else:
				if key in fields:
					params["_fid_"+fields[key]] = value
		params = dict(params,**options)
		return self.request(params,tableID)

	#Deletes the record specified by rid from the table given by tableID
	def deleteRecord(self,tableID,rid):
		params = {'act':'API_DeleteRecord','rid':rid}
		return self.request(params,tableID)

	#Deletes every record from tableID selected by query
	def purgeRecords(self,tableID,query):
		params = {'act':'API_PurgeRecords','query':query}
		return self.request(params,tableID)

	#Returns a dict containing fieldname:fieldid pairs
	#Field names will have spaces replaced with not spaces
	def getFields(self,tableID):
		params = {'act':'API_GetSchema'}
		schema = self.request(params,tableID)
		fields = schema.find('table').find('fields')
		fieldlist = {}
		for field in fields:
			label = field.find('label').text.lower().replace(' ','')
			fieldlist[label] = field.attrib['id']
		return fieldlist

	#Returns a dict of tablename:tableID pairs
	#This is called automatically after successful authentication
	def _getTables(self):
		if self.appid == None:
			return {}
		params = {'act':'API_GetSchema'}
		schema = self.request(params,self.appid)
		chdbs = schema.find('table').find('chdbids')
		tables = {}
		for chdb in chdbs:
			tables[chdb.attrib['name'][6:]] = chdb.text
		return tables

	#Executes a query on tableID
	#Returns a list of dicts containing fieldname:value pairs. record ID will always be specified by the "rid" key
	def query(self,tableID,query):
		params = dict(query)
		params['act'] = "API_DoQuery"
		params['includeRids'] = '1'
		params['fmt'] = "structured"
		records = self.request(params,tableID).find('table').find('records')
		data = []
		fields = {fid:name for name,fid in list(self.getFields(tableID).items())}
		for record in records:
			temp = {}
			temp['rid'] = record.attrib['rid']
			for field in record:
				if(field.tag == "f"):
					temp[fields[field.attrib['id']]] = field.text
			data.append(temp)
		return data

	#Emulates the syntax of basic (SELECT,DELETE) SQL queries
	#Example: qb.sql("SELECT * FROM users WHERE name`EX`John\_Doe OR role`EX`fakeperson") #The \_ represents a space. This is a very basic function that doesn't use state machines. Note: field and table names will not have spaces
	#Example: qb.sql("SELECT firstname|lastname FROM users WHERE paid`EX`true ORDER BY lastname ASC LIMIT 100")
	#Example: qb.sql("DELETE FROM assets WHERE value`BF`0")
	#I encourage you to modify this to suit your needs. Please contribute this back to the Python-QuickBase-SDK repository. Give QuickBase the API it deserves...
	def sql(self,querystr):
		tokens = querystr.split(" ")
		if tokens[0] == "SELECT":
			query = {}
			tid = self.tables[tokens[3]]
			tfields = self.getFields(tid)
			if tokens[1] != "*":
				clist = ""
				for field in tokens[1].split("|"):
					clist += tfields[field]+"."
				query['clist'] = clist[:len(clist)-1]
			if len(tokens) > 4:
				try:
					where = tokens.index("WHERE")
					querystr = ""
					for i in range(where+1,len(tokens)):
						if (i-where+1)%2 == 0:
							filt = tokens[i].split("`")
							querystr += "{'"+tfields[filt[0]]+"'."+filt[1]+".'"+filt[2].replace("\_"," ")+"'}"
						elif tokens[i] == "AND" or tokens[i] == "OR":
							querystr += tokens[i]
						else:
							break
					query['query'] = querystr
				except ValueError:
					pass
				except:
					print("SQL error near WHERE")
					self.error = -2
					return

				try:
					orderby = tokens.index("ORDER")+1
					orderings = tokens[orderby+1].split("|")
					slist = ""
					for ordering in orderings:
						slist += tfields[ordering]+"."
					query['slist'] = slist[:len(slist)-1]
					query['options'] = (query['options']+"." if 'options' in query else "")+"sortorder-"+("A" if tokens[orderby+2] == "ASC" else "D")
				except ValueError:
					pass
				except:
					print("SQL error near ORDER")
					self.error = -2
					return

				try:
					limit = tokens[tokens.index("LIMIT")+1]
					limit = limit.split(",")
					if(len(limit) > 1):
						query['options'] = (query['options']+"." if 'options' in query else "")+"skp-"+limit[0]+".num-"+limit[1]
					else:
						query['options'] = (query['options']+"." if 'options' in query else "")+"num-"+limit[0]
				except ValueError:
					pass
				except:
					print("SQL error near LIMIT")
					self.error = -2
					return

			return self.query(tid,query)

		elif tokens[0] == "DELETE":
			tid = self.tables[tokens[2]]
			tfields = self.getFields(tid)
			where = 3
			querystr = ""
			for i in range(where+1,len(tokens)):
				if (i-where+1)%2 == 0:
					filt = tokens[i].split("`")
					querystr += "{'"+tfields[filt[0]]+"'."+filt[1]+".'"+filt[2]+"'}"
				elif tokens[i] == "AND" or tokens[i] == "OR":
					querystr += tokens[i]
				else:
					break
			return self.purgeRecords(tid,querystr)



