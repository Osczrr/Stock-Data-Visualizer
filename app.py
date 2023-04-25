import sqlite3
from flask import Flask, render_template, request, url_for, flash, redirect, abort
import csv
import requests
import pygal
import re
from datetime import datetime, timedelta
from pygal.style import Style
app = Flask(__name__)
app.config["DEBUG"] = True
app.config['SECRET_KEY'] = 'your secret key'

#################################FUNCTIONS#############################################
api = "ARJ4YHDD7BSSD94B"
stockSymbol = None
stock = None
chartType = None
timeSeries = None
bDate = None
eDate = None

def SetStockSymbol(x):
    global stockSymbol
    stockSymbol = x

def SetStock(new_stock_data):
    global stock
    stock = new_stock_data

def SetChartType(x):
    global chartType
    chartType = x

def SetTimeSeries(x):
    global timeSeries
    timeSeries = x

def SetDates(x:tuple):
    global bDate
    bDate = x[0]
    global eDate
    eDate = x[1]     

def GetApi():
    return api

def GetStockSymbol():
    return stockSymbol

def GetStock():
    return stock
    
def GetChartType():
    return chartType

def GetTimeSeries():
    return timeSeries

def GetBeginningDate():
    return bDate

def GetEndDate():
    return eDate

def create_line_graph():
    return create_graph(GetStock(), pygal.Line())


def create_bar_graph():
    return create_graph(GetStock(), pygal.Bar())

def create_graph(json: dict, graph: pygal.Graph):
    dates = []
    options = { "Open": [], "High": [], "Low": [], "Close": [] }
    data = extract_data(json)
    datetime = string_to_datetime()
    for item in data:
        dates.append(datetime(item["date"]))
        options["Open"].append(float(item["1. open"]))
        options["High"].append(float(item["2. high"]))
        options["Low"].append(float(item["3. low"]))
        options["Close"].append(float(item["4. close"]))
    for opt in options: graph.add(opt, options[opt])
    graph.x_labels = dates
    graph.title = create_title()

    graph_styling(graph, len(dates))
    return graph.render_data_uri()

def string_to_datetime():
    previous = datetime(1, 1, 1)
    time_series = GetTimeSeries()

    def convert(date: str):
        nonlocal previous

        if (time_series == "TIME_SERIES_INTRADAY"):
            day = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
            if (day.date() == previous.date()):
                format = '%H:%M:%S'
            else:
                format = '%Y-%m-%d %H:%M:%S'
                previous = day

            return day.strftime(format)
        else:
            return datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')
    return convert


def get_date(item: dict):
    return item["date"]


def extract_data(json: dict):
    try:
        time_series = [k for k in json.keys() if re.match(r".*Time Series.*", k)][0]
    except IndexError:
        print("Something went wrong....")
    data_points = [{"date": k, **v} for k, v in json[time_series].items()]
    data_points.sort(key = get_date)
    start = get_date_index(data_points, GetBeginningDate())
    end = get_date_index(data_points, GetEndDate())
    return segment_data(data_points, start, end)


def create_title():
    symbol = GetStockSymbol()
    begin = GetBeginningDate()
    end = GetEndDate()
    return f"Stock Data for {symbol}: {begin} to {end}"

def graph_styling(graph: pygal.Graph, point_count: int):
    if (point_count > 100):
        graph.x_labels_major_every = 10
        graph.show_minor_x_labels = False

    graph.style = Style(
        label_font_size = point_count/3,
        major_label_font_size = point_count/3,
        stroke_width = 15,
        legend_font_size = point_count/2,
        title_font_size = point_count,
        tooltip_font_size = point_count/3
    )
    graph.dots_size = 15
    graph.x_label_rotation = 90
    graph.width = point_count * 50
    graph.height = point_count * 25 
    graph.legend_box_size = point_count/3


def get_date_index(data: list, date: str):
    time_series = GetTimeSeries()
    if (time_series == "TIME_SERIES_WEEKLY"):
        date: datetime = datetime.strptime(date, "%Y-%m-%d")
        dates = [date]
        for i in range(-3,4):
            week_day = (date + timedelta(days=i)).strftime("%Y-%m-%d")
            print(week_day)
            for k in range(len(data)):
                if week_day in data[k]["date"]:
                    return k
        return -1

    if (time_series == "TIME_SERIES_MONTHLY"):
        date = datetime.strptime(date, "%Y-%m-%d").strftime("%Y-%m")

    for i in range(len(data)):
        if date in data[i]["date"]:
            return i
    return -1


def segment_data(data:list, start:int, end:int):
    start = start if start != -1 else 0
    end = end if end != -1 else len(data)
    return [data[i] for i in range(start, end)]

def pullStock():
    if GetTimeSeries() == "TIME_SERIES_INTRADAY":
        url = f"https://www.alphavantage.co/query?function={GetTimeSeries()}&symbol={GetStockSymbol()}&interval=15min&apikey={GetApi()}"
    else:
        url = f"https://www.alphavantage.co/query?function={GetTimeSeries()}&symbol={GetStockSymbol()}&apikey={GetApi()}"
    r = requests.get(url)
    data = r.json()

    SetStock(data)

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_post(post_id):
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    conn.close()

    if post is None:
        abort(404)
    
    return post


@app.route("/", methods=['GET', 'POST'])
def stocks():
    with open('stocktickers.csv', newline='') as csvfile:
        csv_data = list(csv.reader(csvfile))
    if request.method == "GET":
        return render_template("stock.html", csv_data=csv_data)
    if request.method == "POST":
        symbol = request.form['symbol']
        chart_type = request.form['Chart_Type']
        time_series = request.form['Time_Series']
        if time_series == "Daily":
            time_series = "TIME_SERIES_DAILY_ADJUSTED"
        if time_series == "Weekly":
            time_series = "TIME_SERIES_WEEKLY"
        if time_series == "Monthly":
            time_series = "TIME_SERIES_MONTHLY"
        if time_series == "Intraday":
            time_series = "TIME_SERIES_INTRADAY"
        elif time_series == "":
            flash("Time Series required")
        bDate = request.form['bDate']
        eDate = request.form['eDate']
        try:
            eDate_str = datetime.strptime(eDate, "%Y-%m-%d").strftime("%Y-%m-%d")
            bDate_str = datetime.strptime(bDate, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            print("Times not listed....")
        if symbol == "":
            flash("Symbol is required!")
        if chart_type == "":
            flash("Chart type required!")
        if not bDate:
            flash('Beginning Date required!')
        if not eDate:
            flash("Ending Date required!")
        elif not (eDate > bDate):
            flash("Start date must be before end date!")
        else:
            SetStockSymbol(symbol)
            SetChartType(chart_type)
            SetTimeSeries(time_series)
            SetDates((bDate_str, eDate_str))
            pullStock()
            try:
                if chart_type == 'line':
                    graph_uri = create_line_graph()
                else:
                    graph_uri = create_bar_graph()
                    
                return render_template("stock.html", csv_data=csv_data, graph_uri=graph_uri)
            except Exception as e:
                flash("Cannot find information for this query- did you enter it correctly?")
                return redirect(url_for('stocks'))
    return render_template("stock.html", csv_data=csv_data)
if __name__ == '__main__':
    app.run(host="0.0.0.0")
