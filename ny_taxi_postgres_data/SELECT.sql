SELECT
    tpep_pickup_datetime,
    tpep_dropoff_datetime,
    total_amount,
    CONCAT(zpu."Borough", '/', zpu."Zone") AS "pickup_loc",
    CONCAT(zdo."Boroguh", '/', zdo."Zone") AS "dropoff_loc"
FROM
    yellow_taxi_trips t,
    JOIN taxi_zone_lookup zpu ON t."PULocationID" = zpu."LocationID"
    JOIN taxi_zone_lookup zdo ON t."DOLocationID" = zdo."LocationID"
LIMIT 100

 
 
 WITH astoria_location AS (
    SELECT zo."LocationID" AS astoria_id
    FROM taxi_zone_lookup zo
    WHERE zo."Zone" = 'Astoria'
 ),
 max_tip AS (
    SELECT MAX(gr."tip_amount") AS max_amount
    FROM green_taxi_data gr
    WHERE gr."PULocationID" = (SELECT astoria_id FROM astoria_location)
 )
 SELECT g."tip_amount",
 z."Zone",
 g."PULocationID",
 g."DOLocationID"
 FROM green_taxi_data g
 JOIN taxi_zone_lookup z ON z."LocationID" = g."DOLocationID" 
 WHERE 
--     g."PULocationID" = (
--         SELECT 
--             zo."LocationID" AS zone_ID 
--         FROM 
--             taxi_zone_lookup zo
--         WHERE zo."Zone" = 'Astoria'
-- ) 
--   AND 
 g."tip_amount" = (SELECT max_amount FROM max_tip); 
    -- (SELECT 
    --      MAX(gr."tip_amount") OVER () AS max_tip
    -- FROM
    --      green_taxi_data gr
    -- WHERE
    --     gr."PULocationID" = zone_ID
    -- );