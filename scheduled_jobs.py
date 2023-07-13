from data.database import save_order, get_all_orders
from products import create_product_download
from apscheduler.schedulers.background import BackgroundScheduler
import requests


def initialise_scheduled_jobs(app):
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=process_orders,
        args=[app],
        trigger="interval",
        seconds=app.config["SCHEDULED_JOB_INTERVAL_SECONDS"],
    )
    scheduler.start()


def process_orders(app):
    with app.app_context():
        orders = get_queue_of_orders_to_process()
        if len(orders) == 0:
            return

        order = orders[0]

        app.logger.info("Processing Order: " + str(order.id))

        payload = {
            "product": order.product,
            "customer": order.customer,
            "date": order.date_placed_local.isoformat(),
        }

        response = requests.post(
                app.config["FINANCE_PACKAGE_URL"] + "/ProcessPayment",
                json=payload
            )

        app.logger.info("Response from endpoint: " + response.text)

        try:
            response.raise_for_status()
        except:
            app.logger.exception("Error processing order {id}".format(id = order.id))

        order.set_as_processed()
        save_order(order)

def get_queue_of_orders_to_process():
    allOrders = get_all_orders()
    queuedOrders = filter(lambda order: order.date_processed == None, allOrders)
    sortedQueue = sorted(queuedOrders, key= lambda order: order.date_placed)
    return list(sortedQueue)
