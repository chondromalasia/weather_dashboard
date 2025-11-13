# Weather Dashboard

This is basic private dashboard that shows data about weather that I use for my own information.
It is hosted here:

weather.beepboop.site

It requires authentication. Please contact me if you would like to see it!

Currently there is really only one page, one that displays the current forecast for a given location and
forecast provider as well as the historical accuracy for that provider.

## Everything that went into it

This is also the public face of my weather harvesting and analyzing project.
Yes it is overkill, but I was just trying to experiment with different technologies.

### Servers

I have a homelab of 3 Intel Nucs that run k3s.
All of the yaml files are hosted in a separate repo, the yaml files are applied by hand.

### General Repo Structure

Each repo involved has a CI/CD pipeline that runs tests, builds the image and pushes it to docker.
I update the image by hand, although now that I'm typing it out, that should/could also be another step.

### Scraping

I am interested scraping forecasts and observations about the weather.
Both produce their output to a kafka topic.

#### Forecasts

Some historical forecasts are maintained in a database (shout out to open-meteo), however others, like the
National Weather Service local forecasts are not.
It is possible to reverse-engineer the forecast from the MOS/NBM but what interests me is the information
available to the general public at a given point in time.
So every hour I call the NWS api for each location I'm interested in.

There are a few websites where I actually scrape data from the website, respecting their robots.txt

#### Observations

At this point in time I scrape one thing and one thing only: the daily climatological report.
Yes this information is available via API (and I have used this api to backfill my database).
However it is often delayed by a day.
AND it does not show you the time of the daily high, which is something I am very interested in.

And while you can query the historical observations of the NWS, this only reports the measure at the time
that it was reported.
So lets say the recorded peak in temperature in KNYC was at 12:32.
KNYC reports its temperatures hourly, so it could be when it reports the temperature that it was a degree below.
So the observation-scraper checks every hour to see if the cli for the previous day's weather has been 
put up on the internet, scrapes the data I need and produces it to kafka.

### Kafka

Yes this is overkill.
But I was curious about Strimzi and just using Python with Kafka.
So I have some Kafka topics up and running.
I can heartily recommend Strimzi.

### Consuming/writing to a Database

I have consumers for Forecasts and Observations, both of which write to a PostgresSQL database.
The Forecast-consumer checks to see if there have been any changes since the previous forecast check
and only writes if there is a change.

### Postgres

This is just a run-of-the-mill PostgresSQL database, running in a Kubernetes Pod.
It is backed up every day to an S3 bucket.

### API

I have an API that does a lot of the querying for me.
If you are in the LAN it is easy to access, however I do not think that I am ready to expose it to the public.
If I am out of my LAN, I have to connect to a VPN in order to access it.

### Analytics

Generally speaking my workflow is that I mess around in a Jupyter notebook and then turn whatever works into a
module or a dashboard.
So I have a separate repo which is just a collection of Jupyter notebooks that I run experiments on.

## Wishes

I have some pretty concrete plans for the next couple of steps.

But the next one is make sort of a 'utils' library. 
There are a number of functions that I find myself re-using, specifically between my notebooks and the dashboard
and it would be nice to have a library that just hosts those that I can install with pip and not worry about
repeated boilerplate code. That is probably the last 'repo' that will be added to this workflow.
