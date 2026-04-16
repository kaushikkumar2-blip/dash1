WITH conv AS (
    SELECT
        shipment_received_at_origin_date_key,
        seller_type,
        CASE
            WHEN LOWER(payment_type) = 'prepaid' THEN 'prepaid'
            ELSE 'cod'
        END AS payment_type,
        COUNT(DISTINCT vendor_tracking_id) AS conv_deno,
        COUNT(DISTINCT CASE
            WHEN LOWER(ekl_shipment_type) = 'forward'
                 AND (LOWER(shipment_current_status) = 'delivered' OR LOWER(shipment_current_status) = 'delivery_update')
            THEN vendor_tracking_id
            ELSE NULL
        END) AS conv_num,
        COUNT(DISTINCT CASE
            WHEN fsd_first_ofd_date_key IS NULL
                 AND first_undelivery_status IS NULL
                 AND last_undelivery_status IS NULL
                 AND shipped_lpd_date_key < rto_create_date_key
            THEN vendor_tracking_id
        END) AS EKL_RTO_num
    FROM
        bigfoot_external_neo.scp_fsgde_ns__externalisation_l1_scala_fact ext
    LEFT JOIN
        bigfoot_external_neo.scp_oms__date_dim_fact dim
        ON ext.shipment_received_at_origin_date_key = dim.date_dim_key
    WHERE
        seller_type IN (
           'ABE', 'ABF', 'AGI', 'AIL', 'AVH', 'BBW', 'BFK', 'BGS', 'BHN', 'BRP', 'BSI', 'CDM', 'CIQ', 'CLQ', 'CLS', 'CMA', 'CMD', 'CQN', 'CRD', 'CSU', 'CUL', 'CUL_NDD', 'DAH', 'DAM', 'DLA', 'DSL', 'DSP', 'ECS', 'EMC', 'EMS', 'FBD', 'FCY', 'FDD', 'FHH', 'FKA', 'FKM', 'FKZ', 'FLN', 'FLS', 'FMB', 'FRD', 'G', 'GBS', 'GKA', 'GKM', 'GKP', 'GKS', 'GLA', 'GOK', 'GSB', 'GSD', 'GSL', 'HKH', 'HOP', 'HSW', 'ILM', 'ILQ', 'ILS', 'IOB', 'JHB', 'JIF', 'JSL', 'KAL', 'KAP', 'KND_NDD', 'KTH', 'LFS', 'LHL', 'LIV', 'LMR', 'LRL', 'MAM', 'MAX', 'MJH', 'MNM', 'MOG', 'MWP', 'MYL', 'MYR', 'NAP', 'NBC', 'NIR', 'NKF', 'NMA', 'NMB', 'NME', 'NMP', 'NMS', 'NUA', 'NYK', 'OIP', 'PFP', 'PFY', 'PGR', 'PIP', 'PLN', 'POP', 'POW', 'PRO', 'PRV', 'PSP', 'RAM', 'RAP', 'RDD', 'RDT', 'REN', 'REW', 'ROM', 'ROP', 'RPB', 'RPG', 'RPS', 'SCL', 'SCR', 'SDB', 'SDI', 'SDL', 'SHC', 'SHO', 'SIS', 'SLS', 'SME', 'SMP', 'SNI', 'SPB', 'SPY', 'SRS', 'SRT', 'SSI', 'TDS', 'TEE', 'TMG', 'TTN', 'VEB', 'VEH', 'VEL', 'VEN', 'VET', 'WML', 'ZIP','ZBI'
        )
    GROUP BY
        1, 2, 3
),

pickup AS (
    SELECT
        shipment_created_at_date_key,
        seller_type,
        CASE
            WHEN LOWER(payment_type) = 'prepaid' THEN 'prepaid'
            ELSE 'cod'
        END AS payment_type,
        COUNT(DISTINCT vendor_tracking_id) AS fm_created,
        COUNT(DISTINCT CASE
            WHEN shipment_received_at_origin_date_key IS NOT NULL THEN vendor_tracking_id
            ELSE NULL
        END) AS fm_picked,
        COUNT(DISTINCT CASE
            WHEN shipment_received_at_origin_date_key = shipment_created_at_date_key THEN vendor_tracking_id
            ELSE NULL
        END) AS fm_d0_picked
    FROM
        bigfoot_external_neo.scp_fsgde_ns__externalisation_l1_scala_fact ext
    LEFT JOIN
        bigfoot_external_neo.scp_oms__date_dim_fact dim
        ON ext.shipment_received_at_origin_date_key = dim.date_dim_key
    WHERE
        seller_type IN (
          'ABE', 'ABF', 'AGI', 'AIL', 'AVH', 'BBW', 'BFK', 'BGS', 'BHN', 'BRP', 'BSI', 'CDM', 'CIQ', 'CLQ', 'CLS', 'CMA', 'CMD', 'CQN', 'CRD', 'CSU', 'CUL', 'CUL_NDD', 'DAH', 'DAM', 'DLA', 'DSL', 'DSP', 'ECS', 'EMC', 'EMS', 'FBD', 'FCY', 'FDD', 'FHH', 'FKA', 'FKM', 'FKZ', 'FLN', 'FLS', 'FMB', 'FRD', 'G', 'GBS', 'GKA', 'GKM', 'GKP', 'GKS', 'GLA', 'GOK', 'GSB', 'GSD', 'GSL', 'HKH', 'HOP', 'HSW', 'ILM', 'ILQ', 'ILS', 'IOB', 'JHB', 'JIF', 'JSL', 'KAL', 'KAP', 'KND_NDD', 'KTH', 'LFS', 'LHL', 'LIV', 'LMR', 'LRL', 'MAM', 'MAX', 'MJH', 'MNM', 'MOG', 'MWP', 'MYL', 'MYR', 'NAP', 'NBC', 'NIR', 'NKF', 'NMA', 'NMB', 'NME', 'NMP', 'NMS', 'NUA', 'NYK', 'OIP', 'PFP', 'PFY', 'PGR', 'PIP', 'PLN', 'POP', 'POW', 'PRO', 'PRV', 'PSP', 'RAM', 'RAP', 'RDD', 'RDT', 'REN', 'REW', 'ROM', 'ROP', 'RPB', 'RPG', 'RPS', 'SCL', 'SCR', 'SDB', 'SDI', 'SDL', 'SHC', 'SHO', 'SIS', 'SLS', 'SME', 'SMP', 'SNI', 'SPB', 'SPY', 'SRS', 'SRT', 'SSI', 'TDS', 'TEE', 'TMG', 'TTN', 'VEB', 'VEH', 'VEL', 'VEN', 'VET', 'WML', 'ZIP','ZBI'
        )
        AND LOWER(ekl_shipment_type) NOT IN ('rvp')
    GROUP BY
        1, 2, 3
),

fac AS (
    SELECT
        tasklist_created_date_key,
        seller_type,
        CASE
            WHEN LOWER(payment_type) = 'prepaid' THEN 'prepaid'
            ELSE 'cod'
        END AS payment_type,
        COUNT(DISTINCT CASE
            WHEN LOWER(tasklist_type) = 'runsheet'
                 AND LOWER(attempt_type) = 'customer'
                 AND shipment_actioned_flag = 1
                 AND attempt_no = 1
            THEN CONCAT(vendor_tracking_id, CAST(tasklist_id AS STRING))
            ELSE NULL
        END) AS First_attempt_delivered,
        COUNT(DISTINCT CASE
            WHEN LOWER(tasklist_type) = 'runsheet'
                 AND LOWER(attempt_type) = 'customer'
                 AND attempt_no = 1
            THEN CONCAT(vendor_tracking_id, CAST(tasklist_id AS STRING))
            ELSE NULL
        END) AS fac_deno,
        COUNT(DISTINCT CASE
            WHEN LOWER(tasklist_type) = 'runsheet'
                 AND LOWER(attempt_type) = 'customer'
            THEN CONCAT(vendor_tracking_id, CAST(tasklist_id AS STRING))
        END) AS total_attempts,
        COUNT(DISTINCT CASE
            WHEN LOWER(tasklist_type) = 'runsheet'
                 AND LOWER(attempt_type) = 'customer'
                 AND shipment_actioned_flag = 1
            THEN CONCAT(vendor_tracking_id, CAST(tasklist_id AS STRING))
            ELSE NULL
        END) AS total_delivered_attempts,
        COUNT(DISTINCT CASE
            WHEN attempt_Type = 'Customer'
                 AND undel_unpick_status = 'Undelivered_Attempted-Request for reschedule'
            THEN CONCAT(vendor_tracking_id, CAST(tasklist_id AS STRING))
        END) AS rfr_num,
        COUNT(DISTINCT CASE
            WHEN attempt_Type = 'Customer'
            THEN CONCAT(vendor_tracking_id, CAST(tasklist_id AS STRING))
            ELSE NULL
        END) AS rfr_deno
    FROM
        bigfoot_external_neo.scp_fsgde_ns__lastmile_tasklist_base_fact task
    LEFT JOIN
        bigfoot_external_neo.scp_oms__date_dim_fact dim
        ON task.tasklist_created_date_key = dim.date_dim_key
    WHERE
        seller_type IN (
           'ABE', 'ABF', 'AGI', 'AIL', 'AVH', 'BBW', 'BFK', 'BGS', 'BHN', 'BRP', 'BSI', 'CDM', 'CIQ', 'CLQ', 'CLS', 'CMA', 'CMD', 'CQN', 'CRD', 'CSU', 'CUL', 'CUL_NDD', 'DAH', 'DAM', 'DLA', 'DSL', 'DSP', 'ECS', 'EMC', 'EMS', 'FBD', 'FCY', 'FDD', 'FHH', 'FKA', 'FKM', 'FKZ', 'FLN', 'FLS', 'FMB', 'FRD', 'G', 'GBS', 'GKA', 'GKM', 'GKP', 'GKS', 'GLA', 'GOK', 'GSB', 'GSD', 'GSL', 'HKH', 'HOP', 'HSW', 'ILM', 'ILQ', 'ILS', 'IOB', 'JHB', 'JIF', 'JSL', 'KAL', 'KAP', 'KND_NDD', 'KTH', 'LFS', 'LHL', 'LIV', 'LMR', 'LRL', 'MAM', 'MAX', 'MJH', 'MNM', 'MOG', 'MWP', 'MYL', 'MYR', 'NAP', 'NBC', 'NIR', 'NKF', 'NMA', 'NMB', 'NME', 'NMP', 'NMS', 'NUA', 'NYK', 'OIP', 'PFP', 'PFY', 'PGR', 'PIP', 'PLN', 'POP', 'POW', 'PRO', 'PRV', 'PSP', 'RAM', 'RAP', 'RDD', 'RDT', 'REN', 'REW', 'ROM', 'ROP', 'RPB', 'RPG', 'RPS', 'SCL', 'SCR', 'SDB', 'SDI', 'SDL', 'SHC', 'SHO', 'SIS', 'SLS', 'SME', 'SMP', 'SNI', 'SPB', 'SPY', 'SRS', 'SRT', 'SSI', 'TDS', 'TEE', 'TMG', 'TTN', 'VEB', 'VEH', 'VEL', 'VEN', 'VET', 'WML', 'ZIP','ZBI'
        )
        AND LOWER(facility_type) NOT IN ('large')
    GROUP BY
        1, 2, 3
),

ofd AS (
    SELECT
        fsd_first_dh_received_date_key,
        seller_type,
        CASE
            WHEN LOWER(payment_type) = 'prepaid' THEN 'prepaid'
            ELSE 'cod'
        END AS payment_type,
        COUNT(DISTINCT CASE
            WHEN fsd_first_dh_received_date_key IS NOT NULL THEN ext.vendor_tracking_id
        END) AS DHin,
        COUNT(DISTINCT CASE
            WHEN fsd_first_dh_received_date_key = fsd_first_ofd_date_key THEN ext.vendor_tracking_id
        END) AS D0_OFD
    FROM
        bigfoot_external_neo.scp_fsgde_ns__externalisation_l1_scala_fact ext
    LEFT JOIN
        bigfoot_external_neo.scp_oms__date_dim_fact dim
        ON ext.fsd_first_dh_received_date_key = dim.date_dim_key
    WHERE
        seller_type IN (
           'ABE', 'ABF', 'AGI', 'AIL', 'AVH', 'BBW', 'BFK', 'BGS', 'BHN', 'BRP', 'BSI', 'CDM', 'CIQ', 'CLQ', 'CLS', 'CMA', 'CMD', 'CQN', 'CRD', 'CSU', 'CUL', 'CUL_NDD', 'DAH', 'DAM', 'DLA', 'DSL', 'DSP', 'ECS', 'EMC', 'EMS', 'FBD', 'FCY', 'FDD', 'FHH', 'FKA', 'FKM', 'FKZ', 'FLN', 'FLS', 'FMB', 'FRD', 'G', 'GBS', 'GKA', 'GKM', 'GKP', 'GKS', 'GLA', 'GOK', 'GSB', 'GSD', 'GSL', 'HKH', 'HOP', 'HSW', 'ILM', 'ILQ', 'ILS', 'IOB', 'JHB', 'JIF', 'JSL', 'KAL', 'KAP', 'KND_NDD', 'KTH', 'LFS', 'LHL', 'LIV', 'LMR', 'LRL', 'MAM', 'MAX', 'MJH', 'MNM', 'MOG', 'MWP', 'MYL', 'MYR', 'NAP', 'NBC', 'NIR', 'NKF', 'NMA', 'NMB', 'NME', 'NMP', 'NMS', 'NUA', 'NYK', 'OIP', 'PFP', 'PFY', 'PGR', 'PIP', 'PLN', 'POP', 'POW', 'PRO', 'PRV', 'PSP', 'RAM', 'RAP', 'RDD', 'RDT', 'REN', 'REW', 'ROM', 'ROP', 'RPB', 'RPG', 'RPS', 'SCL', 'SCR', 'SDB', 'SDI', 'SDL', 'SHC', 'SHO', 'SIS', 'SLS', 'SME', 'SMP', 'SNI', 'SPB', 'SPY', 'SRS', 'SRT', 'SSI', 'TDS', 'TEE', 'TMG', 'TTN', 'VEB', 'VEH', 'VEL', 'VEN', 'VET', 'WML', 'ZIP','ZBI'
        )
    GROUP BY
        1, 2, 3
),

breach AS (
    SELECT
        CAST(FORMAT_DATE('%Y%m%d', DATE(ext.shipped_lpd)) AS INT64) AS shipped_lpd_date_key,
        seller_type,
        CASE
            WHEN LOWER(payment_type) = 'prepaid' THEN 'prepaid'
            ELSE 'cod'
        END AS payment_type,
        COUNT(DISTINCT CASE
            WHEN ext_breach_bucket NOT IN ('01 Future LPD', '02 Delivered by promise', '03 Genuine OFD by promise', '05 RTO by promise')
            THEN vendor_tracking_id
        END) AS Breach_Num,
        COUNT(DISTINCT CASE
            WHEN ext_breach_bucket NOT IN ('01 Future LPD', '02 Delivered by promise', '03 Genuine OFD by promise', '05 RTO by promise')
                 AND DATE_DIFF(
                     COALESCE(
                         PARSE_DATE('%Y%m%d', CAST(fsd_first_ofd_date_key AS STRING)),
                         PARSE_DATE('%Y%m%d', CAST(rto_create_date_key AS STRING)),
                         CURRENT_DATE()
                     ),
                     DATE(shipped_lpd),
                     DAY
                 ) > 1
            THEN vendor_tracking_id
        END) AS breach_plus1_num,
        COUNT(vendor_tracking_id) AS Breach_Den
    FROM
        bigfoot_external_neo.scp_fsgde_ns__externalisation_l1_scala_fact ext
    LEFT JOIN
        bigfoot_external_neo.scp_oms__date_dim_fact dim
        ON CAST(FORMAT_DATE('%Y%m%d', DATE(ext.shipped_lpd)) AS INT64) = dim.date_dim_key
    WHERE
        seller_type IN (
            'ABE', 'ABF', 'AGI', 'AIL', 'AVH', 'BBW', 'BFK', 'BGS', 'BHN', 'BRP', 'BSI', 'CDM', 'CIQ', 'CLQ', 'CLS', 'CMA', 'CMD', 'CQN', 'CRD', 'CSU', 'CUL', 'CUL_NDD', 'DAH', 'DAM', 'DLA', 'DSL', 'DSP', 'ECS', 'EMC', 'EMS', 'FBD', 'FCY', 'FDD', 'FHH', 'FKA', 'FKM', 'FKZ', 'FLN', 'FLS', 'FMB', 'FRD', 'G', 'GBS', 'GKA', 'GKM', 'GKP', 'GKS', 'GLA', 'GOK', 'GSB', 'GSD', 'GSL', 'HKH', 'HOP', 'HSW', 'ILM', 'ILQ', 'ILS', 'IOB', 'JHB', 'JIF', 'JSL', 'KAL', 'KAP', 'KND_NDD', 'KTH', 'LFS', 'LHL', 'LIV', 'LMR', 'LRL', 'MAM', 'MAX', 'MJH', 'MNM', 'MOG', 'MWP', 'MYL', 'MYR', 'NAP', 'NBC', 'NIR', 'NKF', 'NMA', 'NMB', 'NME', 'NMP', 'NMS', 'NUA', 'NYK', 'OIP', 'PFP', 'PFY', 'PGR', 'PIP', 'PLN', 'POP', 'POW', 'PRO', 'PRV', 'PSP', 'RAM', 'RAP', 'RDD', 'RDT', 'REN', 'REW', 'ROM', 'ROP', 'RPB', 'RPG', 'RPS', 'SCL', 'SCR', 'SDB', 'SDI', 'SDL', 'SHC', 'SHO', 'SIS', 'SLS', 'SME', 'SMP', 'SNI', 'SPB', 'SPY', 'SRS', 'SRT', 'SSI', 'TDS', 'TEE', 'TMG', 'TTN', 'VEB', 'VEH', 'VEL', 'VEN', 'VET', 'WML', 'ZIP','ZBI'
        )
    GROUP BY
        1, 2, 3
)

SELECT DISTINCT
    conv.shipment_received_at_origin_date_key AS reporting_date,
    conv.payment_type,
    conv.seller_type,
    EKL_RTO_num AS zero_attempt_num,
    fm_d0_picked,
    fm_picked,
    fm_created,
    conv_num,
    conv_deno AS PHin,
    First_attempt_delivered,
    fac_deno,
    total_delivered_attempts,
    total_attempts,
    DHin,
    D0_OFD,
    rfr_num,
    rfr_deno,
    Breach_Num,
    Breach_Den,
    breach_plus1_num
FROM
    conv
LEFT JOIN
    pickup
    ON pickup.shipment_created_at_date_key = conv.shipment_received_at_origin_date_key
    AND conv.seller_type = pickup.seller_type
    AND conv.payment_type = pickup.payment_type
LEFT JOIN
    fac
    ON conv.shipment_received_at_origin_date_key = fac.tasklist_created_date_key
    AND conv.seller_type = fac.seller_type
    AND conv.payment_type = fac.payment_type
LEFT JOIN
    ofd
    ON conv.shipment_received_at_origin_date_key = ofd.fsd_first_dh_received_date_key
    AND conv.seller_type = ofd.seller_type
    AND conv.payment_type = ofd.payment_type
LEFT JOIN
    breach
    ON conv.shipment_received_at_origin_date_key = breach.shipped_lpd_date_key
    AND conv.seller_type = breach.seller_type
    AND conv.payment_type = breach.payment_type
WHERE
    conv.shipment_received_at_origin_date_key BETWEEN 20220101 AND {end_date};
