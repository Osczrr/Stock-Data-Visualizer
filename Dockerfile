#Use an official python runtime
FROM python:3.8-slim-buster

WORKDIR /app
#Copy code in the current directory to the container /app
COPY . /app
RUN pip install requests
RUN pip install pygal


#Upgrade PIP
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

#Set Default command to run when starting the container
CMD ["python", "app.py"]