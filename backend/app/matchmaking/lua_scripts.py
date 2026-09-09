# Lua script for atomic idempotent match reservation
RESERVE_PAIR_SCRIPT = """
local queue_key = KEYS[1]
local lock_prefix = KEYS[2]

local user_a = ARGV[1]
local match_id = ARGV[2]
local last_partner = ARGV[3]
local lock_ttl = tonumber(ARGV[4])
local now = tonumber(ARGV[5])
local max_queue_time = tonumber(ARGV[6])

-- Evict stale entries first (now - score > max_queue_time)
local min_valid_score = now - max_queue_time
redis.call('ZREMRANGEBYSCORE', queue_key, '-inf', min_valid_score)

-- Check if user_a is already locked
if redis.call('EXISTS', lock_prefix .. user_a) == 1 then
    local existing_match = redis.call('GET', lock_prefix .. user_a)
    return {user_a, existing_match, "LOCKED"}
end

local waiting_users = redis.call('ZRANGE', queue_key, 0, -1)

local user_b = nil
for _, u in ipairs(waiting_users) do
    if u ~= user_a and u ~= last_partner then
        -- Check if locked
        if redis.call('EXISTS', lock_prefix .. u) == 0 then
            user_b = u
            break
        end
    end
end

if user_b then
    -- Match found!
    -- Add user_a to queue (so both are tracked) and lock both
    redis.call('ZADD', queue_key, now, user_a)
    
    redis.call('SET', lock_prefix .. user_a, match_id, 'EX', lock_ttl)
    redis.call('SET', lock_prefix .. user_b, match_id, 'EX', lock_ttl)
    
    return {user_b, match_id, "NEW_MATCH"}
else
    -- No match found, add/update user_a in queue with current timestamp
    redis.call('ZADD', queue_key, now, user_a)
    return nil
end
"""
