FROM python:3.8-slim
LABEL org.opencontainers.image.source https://github.com/openzim/wikihow

# Install necessary packages
RUN apt-get update -y \
    && apt-get install -y --no-install-recommends locales libmagic1 wget ffmpeg \
    libtiff5-dev libjpeg-dev libopenjp2-7-dev zlib1g-dev \
    libfreetype6-dev liblcms2-dev libwebp-dev tcl8.6-dev tk8.6-dev python3-tk \
    libharfbuzz-dev libfribidi-dev libxcb1-dev gifsicle curl unzip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# setup timezone and locale
ENV TZ "UTC"
RUN echo "UTC" >  /etc/timezone \
    && sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && locale-gen
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

# TEMP
RUN wget --progress=dot:giga -L \
    http://tmp.kiwix.org/wheels/libzim-1.0.0.dev3-cp38-cp38-manylinux1_x86_64.whl \
    http://tmp.kiwix.org/wheels/zimscraperlib-1.4.0.dev4-py3-none-any.whl \
    && pip3 install --no-cache-dir ./*.whl \
    && rm ./*.whl

COPY requirements.txt /src/
RUN pip3 install --no-cache-dir -r /src/requirements.txt
COPY wikihow2zim /src/wikihow2zim
COPY setup.py *.md get_js_deps.sh MANIFEST.in /src/
RUN cd /src/ \
    && python3 ./setup.py install \
    && rm -r /src \
    && mkdir -p /output

CMD ["wikihow2zim", "--help"]
