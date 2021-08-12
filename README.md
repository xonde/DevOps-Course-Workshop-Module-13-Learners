# Module 13 Workshop

You will have been given access to a resource group in Azure containing a running the Python app from this repo and SQL database.

Click on the App Service in the Azure portal and then the URL.
You'll see a dashboard showing one successfully processed order and a queue of orders to be processed, but no further orders are being processed.
We need to investigate why.

Back on the App Service in the Azure Portal click on Log stream and you'll see a number of errors like:

```text
requests.exceptions.HTTPError: 400 Client Error: Bad Request for url: https://XXX-order-processing-finance-package.azurewebsites.net/ProcessPayment
```

Sadly this order-processing-finance-package is a third party tool, so we'll need to investigate this issue from our end, and see if we can fix it, or if the problem needs to be raised with the supplier.

Have a look at the source code and identify where the error is thrown.
There is no obvious cause to this issue, but you can see that the system picks up the oldest unprocessed order and tries to process it, here an error is happening, so the order remains unprocessed and will be retired endlessly, so later orders remain unprocessed.

We don't have enough information to work out whats going wrong.
We need more logging.

## Adding more logging to the app

We can add more logging with a line like the following:

```python
app.logger.info("Response from endpoint: " + response.text)
```

If you deploy the code now, this won't actually add anything to the log stream as sadly the default logging level doesn't include `info`.
Add the following to `app.py`

```python
import logging
logging.basicConfig(level=logging.INFO)
```

## Deploy your changes

For the purpose of this workshop it is fine to directly push changes to the app.
In a real setting you are likely to need to push changes to Git and get your CI/CD server to do a release.

In the root of the project run `az login` then `az webapp up -n {App Service name} && az webapp restart`.
webapp name is name of the App Service in the Azure Portal, which is also the first part of the web address (e.g. `XXX-order-processing`)
This will push your current code to the server and restart it.

Subsequent deploys can be done with just `az webapp up && az webapp restart`, as your login and the App Service name name will be remembered.

## Investigate and fix

The log stream should now contain the response from the finance package.
This still isn't quite enough information to fix the problem.
You can add more logging for relevant information as above.

It might also be useful to look at the database.
You can find the details under 'Configuration' for the App Service in the Azure Portal.

Ultimately like so many bugs, investigating is what takes time - the actual fix should just be a single line change.
Having deployed the fix the order that was stuck should be processed, and refreshing the home page of the app should show the queue go down as the orders are gradually processed.

> Note: The next parts assume you leave in the logging added above, so don't remove it when you have fixed the problem.

## Further improvements

You've solved the immediate issue, but there are still some fundamental problems:

* Even when a problem is known the log stream in Azure is quite bad.
* No one will be notified until customers start complaining.
* It's still the case that if something goes wrong with an order all orders will stop.

We need to improve this:

* We should use a tool such as Azure Application Insights (App Insights) to get a better view of the logs.
* We should set up alerts for when something goes wrong.
* Once we have visibility of orders that have failed, perhaps we should move on from them rather than endlessly failing.

## Add App Insights

Within your resource group create a new Application Insights resource.

> Search for "Application Insights" in the top search bar in the portal, select Create, and then select the correct resource group and change the "Resource Mode" to "Classic"

To actually send logs to Application Insights you'll need to add the Python packages opencensus-ext-azure and opencensus-ext-flask to requirements.txt.

Then follow the instructions on that page to add an `AzureLogHandler` to your logger. You should be adding this setup to `app.py`. You can find the "instrumentation key" in the Azure portal, on the overview page of your Application Insights resource.

You can find the "instrumentation key" in the Azure portal, on the overview page of your Application Insights resource. Rather than hardcoding the connection string in the Python code, configure it more securely by using an environment variable called `APPLICATIONINSIGHTS_CONNECTION_STRING`. Set this on the 'Configuration' page of the App Service.

> The environment variable gets picked up automatically so your code doesn't need to pass anything into `AzureLogHandler()`. Just make sure to include `InstrumentationKey=` in the environment variable's value!

A few minutes after deploying your changes (App Insights batches up log messages) you can see the logs.
Go the App Insights resource and then navigate to `Logs`.
The query `traces` should show up all the logging you added in the previous part. All requests to your Flask application should also be getting recorded.
You can also search it with queries like:

```text
traces | where message contains "Response from endpoint"
```

## Add Error Alerts

The second step we wanted to take was to send out alerts when something goes wrong.
We've fixed the problem though, so to start lets add a broken order.
Run the following on the browser console on the app's dashboard:

```javascript
await fetch("/new", {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    product: "TodoApp PRO",
    customer: "Me",
    date_placed: "3000-01-01T12:00:00Z"
})})
```

This order from the year 3000 will fail as it isn't in the past.
It won't actually block new orders as it'll be after them in the queue.

Now search App Insights for `exceptions`.
You won't see any, even though the `traces` will show the expected output.

Exceptions don't automatically appear in App Insights like they did in the log stream so, put a `try...except` block in `scheduled_jobs.py` with the following:

```python
app.logger.exception("Error processing order {id}".format(id = order.id))
```

After deploying this you'll see results when you run the query `exceptions`.
The details of the exception are magically picked up by the logger.
Click "New Alert rule" to setup the rule.

You'll need to click on the condition to set it to alert when there is 1 or more result, and create an action group that sends you an email (or you can skip this if you want - there is also an alert dashboard).

Back in App Insights under Alerts you'll see an alert is raised.
With the default settings this will take up to 5 minutes.
If you set up emails above you'll start to receive these.

## Improve the queue

You'll now receive an email every 5 minutes until Jan 1st 3000.
You probably don't want this.

Now we have alerts in place perhaps rather than endlessly retrying we should give up on orders that error and move on to the next one.

You'll need to make it so when errors are thrown the order is somehow marked as failed, and not to be picked for processing anymore.
Also update the dashboard to mark these failed orders in red.

## Stretch: Queue reliability

To start this stretch scenario run the following in the console on the app's dashboard:

```javascript
 await fetch("/scenario", {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({scenario: "UnreliableProcessing"})})
 ```

After triggering this scenario you should notice a number of orders failing.
It seems that the Finance Package has become quite unreliable and is failing orders at random.
If we retry them it might work.

You need to determine how to recognize such a transient error and stop the app from giving up on such orders, whilst still failing on permanent errors like the one we introduced above.

Having deployed that change, lets reconsider the alerts.

* If an order has failed we always want to send an alert.
* Occasionally having to retry shouldn't trigger and email
* All orders failing even if we are to retry should trigger and email

Change the alerts to fulfil these requirements.

## Stretch: Monitoring load

To start this stretch scenario run the following in the console on the app's dashboard:

```javascript
 await fetch("/scenario", {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({scenario: "HighLoad"})})
 ```

> Note this exercise is to monitor the situation, don't try to fix it as when peak load as passed the queue will be processed.

This system processes orders at a fixed rate (if there are any to be processed of course).
As you can see if that rate is exceeded the queue will build up.
This isn't an exception so won't be caught above but is something to monitor.

We will do this by monitoring the number of requests coming in to create new orders. For that we'll need to add Flask middleware to record requests to App Insights.
Add the `opencensus-ext-flask` package to your `requirements.txt` and add the middleware to `app.py` by adapting this sample code: <https://docs.microsoft.com/en-us/azure/azure-monitor/app/opencensus-python-request#tracking-flask-applications>.

Once you have redeployed your app and given Azure a few minutes to pull the logs through you can run the query "requests" in Application Insights Logs too see all requests made to your application.

We are interested in the number of requests to `/new`. Try the following query:

```text
requests 
| where name == '/new' and success == 'True' 
| project Kind="new", timestamp
| summarize new = count(Kind == "new") by bin(timestamp, 10m)
```

Not very useful in table form, but click "Chart".
This then shows how many orders have been created in 10 minute 'bins'.
Under chart formatting you can chose a better chart type for this type of data too.

Then choose pin to dashboard, and create a new dashboard.
From the Azure Portal you can select dashboard and your new dashboard from the dropdown at the top.
There is an "open editing pane" button on the chart that lets you edit it some more.

This query only tells half the story - how much goes on to the queue not how much leaves it.
From your existing `traces` you should be able to create a chart of successfully processed orders.
With the `union` command you can combine these into a single chart.
Finally, using the existing commands you can add a third data series - how much the queue has increased or decreased by in that time period.

You can set an alert for when the queue is growing.
Prior to increasing the load you'll likely see 10 minute periods where the queue increased or decreased by one or so, so you'll want to set a slightly higher threshold than that.
You'll need to set the alert logic to based on metric measurement and change the summarize line to something like:

```text
| summarize AggregatedValue= count(Kind == "new") -  count(Kind == "processed") by bin(timestamp,  5m)
```

## Stretch: system monitoring

To start this stretch scenario run the following in the console on the app's dashboard:

```javascript
 await fetch("/scenario", {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({scenario: "VeryHighLoad"})})
 ```

If the load ramps up much more this will actually overwhelm the system.

The resources we need to monitor are the database and App Service Plan in your resource group.
You can see metrics on the main page of the resource and pin them to the dashboard, or on the Metrics page there is a larger selection of metrics to graph and pin.

After around 15 minutes the app will stop accepting new orders.
Identify which resource is at fault, and what there is a shortage of.
Now fix the problem.
As a rule of thumb storage is quite cheap to increase (as long as it isn't hugely excessive), so if that is the issue see if you can increase it.
CPU and RAM are often much more expensive to increase, so if that's the problem its often worth investigating if the code can be fixed to reduce its requirement.

Make sure that you have alerts set up so that if you run out again there will be an email giving some notice.

After about half an hour of an order being placed every second you should notice the processing speed slows down.
See if you can use the logging to work out and fix what is causing the problem, which will require performance tuning in the Python code.
