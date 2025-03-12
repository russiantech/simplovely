"""Basic connection example.
"""

import redis

r = redis.Redis(
    host='redis-10540.c14.us-east-1-2.ec2.redns.redis-cloud.com',
    port=10540,
    decode_responses=True,
    username="default",
    password="0P1prFA1uGbFzZKuhOqZmQrxM64SOTmk",
)

success = r.set('foo', 'bar')
# True

result = r.get('foo')
print(result)
# >>> bar
