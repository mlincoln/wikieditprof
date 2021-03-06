import flask
import flask.views
import os
import functools
import urllib2
import re
import operator
import webbrowser
import sys
#import pytrends
from flask import g
from datetime import datetime
from bs4 import BeautifulSoup

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

class Remote(flask.views.MethodView):
    def get(self):
        return flask.render_template('remote.html')

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

def prepare(wikiid):
##    resp = requests.get(wikiurl)
    global wikiurl
    wikiurl = wikiid
#trim full wikipedia url down
    wikiurl = wikiurl.replace("https://en.wikipedia.org/wiki/","")
#clean up weird punctuation?
    wikiurl = urllib2.quote(wikiurl)
    startTime = datetime.now()
    offset = ""
    matchlist = ""
    matchdict = {}
    totalmatches = 0
    return scrapewiki(offset, matchlist, matchdict, totalmatches, startTime)

def scrapewiki(offset, matchlist, matchdict, totalmatches, startTime):
    matchesonpage = 0
    global numrequests
    numrequests = 1300
    url = "http://en.wikipedia.org/w/index.php?title=" + wikiurl + "&offset=" + offset + "&limit=" + str(numrequests) + "&action=history"
    page = opener.open(url)
    offset = ""

    soup = BeautifulSoup(opener.open(url),"html.parser")
# populate matchdict
    for link in soup.find_all("a", class_="mw-changeslist-date"):
        totalmatches += 1
        stime, sday, smonth, syear = map(str, link.string.split(' '))
        yyyymmdd = datetime.strptime(syear+"-"+smonth+"-"+sday, '%Y-%B-%d')
        if yyyymmdd in matchdict:
            matchdict[yyyymmdd] += 1
        else:
            matchdict[yyyymmdd] = 1
#find offset
    for link in soup.find_all("a", class_="mw-nextlink"):
        offset = link.get('href')
        offset = re.search('offset=(\d{14})', offset).group(1)
#determine if we need to go to next page
    if offset != "":
        if (datetime.now()-startTime).total_seconds() > 18:
            return dumpresults(matchlist, matchdict, totalmatches, startTime)
        else:
            return scrapewiki(offset, matchlist, matchdict, totalmatches, startTime)
    else:
        return dumpresults(matchlist, matchdict, totalmatches, startTime)

def dumpresults(matchlist, matchdict, totalmatches, startTime):
    sortdict = (sorted(matchdict.iteritems(), key=operator.itemgetter(1), reverse=True))
    if not matchdict:
        return flask.Markup("<br>Uh oh! That doesn't appear to be a Wikipedia URL. Please try again. <br><br>Your query should look something like https://en.wikipedia.org/wiki/Vladimir_Nabokov")
    maxeditday = max(matchdict.iteritems(), key=operator.itemgetter(1))[0]
    timeTotal = datetime.now()-startTime
    datecreated = sorted(matchdict)[0]
    output = ""
    output += "<br>"
    if totalmatches >= numrequests -1:
        output += 'This wikipedia page has more edits in its history than can be handled by this app at this time. Shown below is information on the most recent ' + str(numrequests) + ' edits.<br><br>'

    output += str(totalmatches) + " edits have been made to this page since "
    if totalmatches >= numrequests -1:
        output += datecreated.strftime('%Y/%m/%d') + ".<br>"
    else:
        output += "it was created on " + datecreated.strftime('%Y/%m/%d') + ".<br>"
    maxeditdaystr = maxeditday.strftime('%Y%-m%d')
    output += 'The highest number of edits (' + str(matchdict[maxeditday]) + ') to the <a href="http://en.wikipedia.org/wiki/' + wikiurl + '">' + wikiurl + '</a> page occurred on <a href="http://en.wikipedia.org/w/index.php?title=' + wikiurl + '&offset=' + str(int(maxeditdaystr)+1) + '000000&limit=' + str(matchdict[maxeditday]) + '&action=history">' + maxeditday.strftime('%Y/%m/%d') + '</a>.<br><br>'

#convert matchdict to yeardict
    yeardict = {}
    for key in matchdict:
        if key.year not in yeardict:
            yeardict[key.year] = [0]*12
        yeardict[key.year][key.month-1] += matchdict[key]
        firstyear = min(yeardict)
        lastyear = max(yeardict)
        currentyear = firstyear + 1
        span = lastyear - firstyear + 1
#plug in blank rows for any years when there were no edits
        while currentyear < lastyear:
            if currentyear not in yeardict:
                yeardict[currentyear] = [0]*12
            currentyear += 1

#find maximum
    maxmonth = 0
    for key in yeardict:
        for item in yeardict[key]:
            if item > maxmonth:
                maxmonth = item

    color = maxmonth
    color = 255/float(color)
    monthtrunc = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
# turns yeardict into an html table with colors based on activity
#    sys.stdout.write(str(yeardict))
#    sys.stdout.flush()
    htmltable = '<table style="width:100%; border-collapse:collapse; border-width:0px;"><tr><td></td>'
    for month in monthtrunc:
        htmltable += '<td>' + month + '</td>'
    htmltable += '</tr>'
    for key in yeardict:
        htmltable += '<tr><td>'+str(key)+'</td>'
        for i in range(0, 12):
            if yeardict[key][i] == 0:
                htmltable += '<td style="background-color:rgba(235,235,235,1);">%s</td>' % (str(yeardict[key][i]))
            else:
                red = yeardict[key][i]*color
                green = (maxmonth-yeardict[key][i])*color
                editspermonth = str(yeardict[key][i])
                year = str(key)
                month = str(i+1)
                if len(month) == 1:
                    month = "0" + month
                htmltable += '<td id="cells" style="background-color:rgba(%i,%i,0,1);"><a href="http://en.wikipedia.org/w/index.php?title=%s&dir=prev&offset=%s%s00000000&limit=%s&action=history">%s</a></td>' % (red, green, wikiurl, year, month, editspermonth, editspermonth)
        htmltable += '</tr>'
    htmltable += "</table>"

    output += htmltable
    output += '<br>This code took '+str(timeTotal)+" seconds to execute."
    output = "<div class='responsestyle'>" + output + "</div>"
    return flask.Markup(output)

port = int(os.environ.get('PORT', 5000))
app.debug = True
app.run(host='0.0.0.0', port=port)
