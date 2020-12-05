#!/usr/bin/env python3
"""
Script to send webhooks from fail2ban actions
"""
from argparse import ArgumentParser
from datetime import datetime, timedelta
from ipaddress import ip_address
from os import getenv

from geoip2 import database
from geoip2.errors import AddressNotFoundError
from pytz import timezone
from requests import Session, post


def createPayload(args):
    """
    Creates the payload
    """

    discordUrl = "https://discord.com/api/webhooks/"
    hookUser = "Fail2Ban"
    action = args.action
    fails = args.fail
    hook = args.hook
    ip = args.ip
    jail = args.jail
    time = args.time
    user = args.user

    webhook = {
        "embeds": [
            {
                "author": {"name": hookUser},
                "timestamp": str(datetime.utcnow())
            }
        ]
    }

    if not user:
        pass
    elif user == "None":
        pass
    elif user.isnumeric():
        webhook["content"] = f"<@{int(user)}>"
    else:
        webhook["content"] = user

    embed = {}
    if "ban" in action:

        data = getGeoData(args)

        if ip is not None:
            embed["url"] = "https://db-ip.com/" + ip
            embed["fields"] = [{"name": f":flag_{data['iso'].lower()}:", "value": data["city"]
                                or data["name"], "inline": True}]
        if data.get('map_embed'):
            embed["image"] = {"url": data['map_embed']}

    if action == "ban":
        embed["title"] = f"New ban on `{jail}`" if jail else "New ban"
        embed["color"] = 16194076
        embed["fields"].append({"name": "Map", "value": f"[Link]({data['map_url']})", "inline": True})
        embed["fields"].append({"name": "Unban cmd", "value": f"```bash\nfail2ban-client unban {ip}\n```"})

        if not time.isnumeric():
            description = f"**{ip}** got banned for `{int(time)}` after `{fails}` tries"
        else:
            tz = timezone(getenv('TZ', 'UTC'))
            time_ = (datetime.now(tz) + timedelta(0, float(time))).strftime('%Y-%m-%d %H:%M:%S %Z%z')
            description = f"**{ip}** got banned for `{fails}` failed attempts, unbanning at `{time_}`"
        embed["description"] = description

    elif action == "unban":
        embed["title"] = f"Revoked ban on `{jail}`"
        embed["description"] = f"**{ip}** is now unbanned"
        embed["color"] = 845872

    elif action == "start":
        webhook["content"] = ""
        embed["description"] = f"Started `{jail}`"
        embed["color"] = 845872

    elif action == "stopped":
        webhook["content"] = ""
        embed["description"] = f"Stopped `{jail}`"
        embed["color"] = 16194076

    webhook["embeds"][0].update(embed)
    post(url=discordUrl + hook, json=webhook)


def getGeoData(args):
    """
    Gets the required Geo based data
    """

    data = {}
    geoIpDB = args.db
    mapKey = args.map_key
    ip = args.ip
    private = not ip_address(ip).is_private

    reader = None
    if private:
        try:
            reader = database.Reader(geoIpDB)
        except FileNotFoundError:
            pass
        except AddressNotFoundError:
            pass
        except Exception as e:
            print('FATAL ERROR: %s', e)

    if reader:
        city = reader.city(ip)
        geoData = {'iso': city.country.iso_code, "name": city.country.name, "city": city.city.name}
        lat = city.location.latitude
        lon = city.location.longitude
        reader.close()
        data = {**data, **geoData}

        session = Session()

        url_params = {"center": f"{lat},{lon}", "size": "500,300"}
        data['map_url'] = session.get('https://mapquest.com/', params=url_params).url

        try:
            img_params = {"center": f"{lat},{lon}", "size": "500,300", "key": mapKey}
            response = session.get('https://www.mapquestapi.com/staticmap/v5/map', params=img_params)
            assert response.status_code == 200
            data['map_embed'] = response.url
        except AssertionError:
            print('Map api not found')
        session.close()
    return data


if __name__ == "__main__":
    parser = ArgumentParser(description='Discord notifier for F2B')
    parser.add_argument('-a', '--action', help="Which F2B action triggered the script",
                        required=True, choices=["unban", "ban", "start", "stop", "test"])
    parser.add_argument('-d', '--db', help="Location to geoip database")
    parser.add_argument('-f', '--fail', help="Amount of attempts done")
    parser.add_argument('-i', '--ip', help="Ip which triggered the action", default="1.1.1.1")
    parser.add_argument('-j', '--jail', help="jail which triggered the action")
    parser.add_argument('-m', '--map-key', help="API key for mapquest")
    parser.add_argument('-t', '--time', help="The time the action is valid")
    parser.add_argument('-u', '--user', help="Discord user, if it is a id, it will tag")
    parser.add_argument('-w', '--hook', help="Discord hook to use.")

    args = parser.parse_args()

    if not args.db:
        if getenv('F2B_GEO_DB'):
            args.db = getenv('F2B_GEO_DB')
        else:
            args.db = '/config/geoip2db/GeoLite2-City.mmdb'
    if not args.hook:
        args.hook = getenv('DISC_HOOK') or getenv('F2B_DISCORD_HOOK')
    if not args.map_key:
        args.map_key = getenv('DISC_API') or getenv('F2B_MAP_KEY')
    if not args.user:
        args.user = getenv('DISC_ME') or getenv('F2B_DISCORD_USER') or None

    createPayload(args)
