#!/usr/local/bin/python3.3

import urllib.request, urllib.parse, urllib.error
#import urllib		#Use this line instead of the previous for Python < 3.0
import xml.etree.ElementTree as elementree
import re
import string

class QBConn:
	def __init__(self,url,appid,token=None,realm=""):
		self.url = url
		self.token = token
		self.appid = appid
		self.ticket = None
		self.realm = realm
		self.error = 0
		self.tables = {}

	def authenticate(self,username,password):
		params = {'act':'API_Authenticate','username':username,'password':password}
		resp = self.request(params,'main')
		if self.error != 0:
			return
		else:
			self.ticket = resp.find("ticket").text
			self.tables = self._getTables()

	def request(self,params,url_ext):
		url = self.url
		url += url_ext
		params['ticket'] = self.ticket
		params['apptoken'] = self.token
		params['realmhost'] = self.realm
		urlparams = urllib.parse.urlencode(params)								#urllib.urlencode(params)
		resp = urllib.request.FancyURLopener().open(url+"?"+urlparams).read()	#urllib.FancyURLopener().open(url+"?"+urlparams).read()
		if re.match('^\<\?xml version=',resp.decode("utf-8")) == None:
			print("No useful data received")
			self.error = -1		#No XML data returned
		else:
			tree = elementree.fromstring(resp)
			self.error = int(tree.find('errcode').text)
			return tree

	def addRecord(self,tableID,data):
		fields = self.getFields(tableID)
		params = {'act':'API_AddRecord'}
		for field in data:
				if field in fields:
					params["_fid_"+fields[field]] = data[field]
		return self.request(params,tableID)

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
		print(params)
		return self.request(params,tableID)

	def getFields(self,tableID):
		params = {'act':'API_GetSchema'}
		schema = self.request(params,tableID)
		fields = schema.find('table').find('fields')
		fieldlist = {}
		for field in fields:
			label = field.find('label').text.lower().replace(' ','')
			fieldlist[label] = field.attrib['id']
		return fieldlist

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
							querystr += "{'"+tfields[filt[0]]+"'."+filt[1]+".'"+filt[2]+"'}"
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
					print("SQL error near LIMIT")
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


