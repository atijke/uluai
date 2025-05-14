FROM python:3.11.11-bookworm
RUN useradd -m app
WORKDIR /home/app
USER app
COPY ./src .
RUN pip install --requirement requirements.txt
EXPOSE 8000
CMD ["python", "-u", "main.py"]