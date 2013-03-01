import flask
import flask.views
import os
import functools
import urllib2
import re
import operator
import webbrowser
import sys
from datetime import datetime
opener = urllib2.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0')]
app = flask.Flask(__name__)
app.secret_key = "bacon"

#redis/background job stuff commented out for now
#import requests
#from rq import Queue
#from worker import conn

#q = Queue(connection=conn)

#users = {'user':'pass'}

class Main(flask.views.MethodView):

    def get(self):
        return flask.render_template('remote.html')

#     def post(self):
#         if 'logout' in flask.request.form:
#             flask.session.pop('username', None)
#             return flask.redirect(flask.url_for('index'))
#         required = ['username', 'passwd']
#         for r in required:
#             if r not in flask.request.form:
#                 flask.flash("Error: {0} is required.".format(r))
#                 return flask.redirect(flask.url_for('index'))
#         username = flask.request.form['username']
#         passwd = flask.request.form['passwd']
#         if username in users and users[username] == passwd:
#             flask.session['username'] = username
#         else:
#             flask.flash("Username doesn't exist or incorrect password")
#         return flask.redirect(flask.url_for('index'))

# def login_required(method):
#     @functools.wraps(method)
#     def wrapper(*args, **kwargs):
#         if 'username' in flask.session:
#             return method(*args, **kwargs)
#         else:
#             flask.flash("A login is required to see the page!")
#             return flask.redirect(flask.url_for('index'))
#     return wrapper

class Remote(flask.views.MethodView):
#     @login_required
    def get(self):
        return flask.render_template('remote.html')

#     @login_required
    def post(self):
        input = flask.request.form['expression']
##        result = q.enqueue(prepare, input)
        result = prepare(input)
##        result = eval(flask.request.form['expression'])
        #flask.flash(result)
        return flask.render_template('remote.html', result=result)

app.add_url_rule('/',
                 view_func=Main.as_view('index'),
                 methods=["GET", "POST"])
app.add_url_rule('/remote/',
                 view_func=Remote.as_view('remote'),
                 methods=['GET', 'POST'])

def prepare(wikiurl):
##    resp = requests.get(wikiurl)
    sys.stdout.write("***prepare***\n")
    sys.stdout.flush()
    wikiurl = wikiurl.replace("%", "%25")
    wikiurl = wikiurl.replace("'", "%27")
    wikiurl = wikiurl.replace("&", "%26")
    startTime = datetime.now()
    offset = ""
    matchlist = ""
    matchdict = {}
    monthdict = {}
    totalmatches = 0
    output = "Profiling the "+wikiurl+" page...\n"
    return scrapewiki(wikiurl, offset, matchlist, matchdict, totalmatches, startTime, output, monthdict)

def scrapewiki(wikiurl, offset, matchlist, matchdict, totalmatches, startTime, output, monthdict):
    sys.stdout.write("***scrapewiki***\n")
    sys.stdout.flush()
    matchesonpage = 0
    url = "http://en.wikipedia.org/w/index.php?title="+wikiurl+"&offset="+offset+"&limit=500&action=history"
    page = opener.open(url)
    while True:
        currentline = page.readline()
        if re.search(wikiurl+'\&amp;offset=(\d{14})', currentline):
            offset = re.search(wikiurl+'\&amp;offset=(\d{14})', currentline).group(1)
        if re.search(r'mw-changeslist-date">(\d{2}:\d{2}),\s{1}(\d{1,2})\s{1}(\w{3,10})\s{1}(\d{4})', currentline):
            matchesonpage += 1
            edittimestamp = re.search(r'mw-changeslist-date">(\d{2}:\d{2}),\s{1}(\d{1,2})\s{1}(\w{3,10})\s{1}(\d{4})', currentline)
            time = edittimestamp.group(1)
            day = edittimestamp.group(2)
            month = edittimestamp.group(3)
            monthlist = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
            if month in monthlist:
                month = "%02d" % (monthlist.index(month)+1)
            year = edittimestamp.group(4)
            if len(str(month)) > 2:
                sys.stdout.write("***month is fucked***\n")
            if len(str(year)) < 4:
                sys.stdout.write("***year is effed***\n")
            ddmmyyyy = str(day+"-"+month+"-"+year)
            yyyymm = str(year+"-"+month)
            sys.stdout.write(yyyymm+"\n")
            if ddmmyyyy in matchdict:
                matchdict[ddmmyyyy] += 1
            else:
                matchdict[ddmmyyyy] = 1
            if yyyymm in monthdict:
                monthdict[yyyymm] += 1
            else:
                monthdict[yyyymm] = 1
            matchlist += time + "\t" + day + "\t" + month + "\t" + year + "\n"
            totalmatches += 1
        if len(currentline) == 0:
##            output += "matches found on first page: "+str(matchesonpage)+"\n"
            if matchesonpage >= 499 and offset != "":
                return recursion(wikiurl, offset, matchlist, matchdict, totalmatches, startTime, output, monthdict)
                break
            else:
                return dumpresults(wikiurl, offset, matchlist, matchdict, totalmatches, startTime, output, monthdict)
                break

def recursion(wikiurl, offset, matchlist, matchdict, totalmatches, startTime, output, monthdict):
    sys.stdout.write("***recursion***\n")
    sys.stdout.flush()
    url = "http://en.wikipedia.org/w/index.php?title="+wikiurl+"&offset="+offset+"&limit=500&action=history"
    page = opener.open(url)
    matchesonpage = 0
    while True:
        currentline = page.readline()
        if re.search(wikiurl+'\&amp;offset=(\d{14})', currentline):
            if re.search(wikiurl+'\&amp;offset=(\d{14})', currentline).group(1) < offset:
                offset = re.search(wikiurl+'\&amp;offset=(\d{14})', currentline).group(1)
        if re.search(r'mw-changeslist-date">(\d{2}:\d{2}),\s{1}(\d{1,2})\s{1}(\w{3,10})\s{1}(\d{4})', currentline):
            matchesonpage += 1
            edittimestamp = re.search(r'mw-changeslist-date">(\d{2}:\d{2}),\s{1}(\d{1,2})\s{1}(\w{3,10})\s{1}(\d{4})', currentline)
            time = edittimestamp.group(1)
            day = edittimestamp.group(2)
            month = edittimestamp.group(3)
            monthlist=["January","February","March","April","May","June","July","August","September","October","November","December"]
            if month in monthlist:
                month = "%02d" % (monthlist.index(month)+1)
            year = edittimestamp.group(4)
            ddmmyyyy = str(day+"-"+month+"-"+year)
            if ddmmyyyy in matchdict:
                matchdict[ddmmyyyy]+=1
            else:
                matchdict[ddmmyyyy]=1
            if str(ddmmyyyy)[3:] in monthdict:
                monthdict[str(ddmmyyyy)[3:]]+=1
            else:
                monthdict[str(ddmmyyyy)[3:]]=1
            matchlist += time + "\t" + day + "\t" + month + "\t" + year + "\n"
            totalmatches += 1
        if len(currentline)==0 and matchesonpage<499:
            return dumpresults(wikiurl,offset,matchlist,matchdict,totalmatches,startTime,output,monthdict)
            break
        if len(currentline)==0:
            if matchesonpage>=499:
                return recursion(wikiurl,offset,matchlist,matchdict,totalmatches,startTime,output,monthdict)
                break
            
def dumpresults(wikiurl,offset,matchlist,matchdict,totalmatches,startTime,output,monthdict):
    sortdict = (sorted(matchdict.iteritems(), key=operator.itemgetter(1), reverse=True))
    output+="A total of "+str(totalmatches)+" edits have been made to this page\n"
    maxeditday = max(matchdict.iteritems(), key=operator.itemgetter(1))[0]
    output += "The highest number of edits ("+ str(matchdict[maxeditday]) + ') to the <a href="http://en.wikipedia.org/wiki/'+wikiurl+'">'+wikiurl+"</a> page occurred on " + str(maxeditday) + " (dd/mm/yyyy).\n"
    timeTotal=datetime.now()-startTime

# this turns monthdict into yeardict so we can make nice horizontal tables
    yeardict = {}
    for key in monthdict:
        try:
            dyear, dmonth = map(int, key.split('-'))
        except Exception:
            continue
        if dmonth not in range(1,13):
            break
        if dyear not in yeardict:
            yeardict[dyear] = [0]*12
        yeardict[dyear][dmonth-1] = monthdict[key]

    output += 'This code took '+str(timeTotal)+" seconds to execute\n"
    color = max(monthdict.iteritems(),key=operator.itemgetter(1))[0]
    color = monthdict[color]
    maxeditmonth = color
    color = 255/float(color)
# turns yeardict into an html table with colors based on activity
    htmltable = '<table border="1"><tr><td></td><td>Jan</td><td>Feb</td><td>Mar</td><td>Apr</td><td>May</td><td>Jun</td><td>Jul</td><td>Aug</td><td>Sep</td><td>Oct</td><td>Nov</td><td>Dec</td></tr>'    
    for key in yeardict:
        htmltable += '<tr><td>'+str(key)+'</td>'
        for i in range(0,12):
            htmltable += '<td style="background-color:rgba(%i,%i,0,1);">%s</td>' % (yeardict[key][i]*color, (maxeditmonth-yeardict[key][i])*color , str(yeardict[key][i]))
        htmltable += '</tr>'
    htmltable += "</table>"

    output += htmltable
    sys.stdout.write("Output is: " + output+"\n")
    sys.stdout.write(str(monthdict)+"\n")
    sys.stdout.flush()
    return flask.Markup(output)
    
port = int(os.environ.get('PORT', 5000))
app.debug = True
app.run(host='0.0.0.0', port=port)
