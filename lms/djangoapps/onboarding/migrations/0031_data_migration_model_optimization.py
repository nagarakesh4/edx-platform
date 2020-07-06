# -*- coding: utf-8 -*-
# Generated by Django 1.11.21 on 2020-07-01 08:12
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('onboarding', '0030_add_new_fields_for_model_optimization'),
    ]

    operations = [
        migrations.RunSQL(
            ["BEGIN;",

             "UPDATE onboarding_userextendedprofile SET function_areas = CONCAT(function_areas, 'function_strategy_planning,') WHERE function_strategy_planning = 1;",
             "UPDATE onboarding_userextendedprofile SET function_areas = CONCAT(function_areas, 'function_leadership_governance,') WHERE function_leadership_governance = 1;",
             "UPDATE onboarding_userextendedprofile SET function_areas = CONCAT(function_areas, 'function_program_design,')	WHERE function_program_design = 1;",
             "UPDATE onboarding_userextendedprofile SET function_areas = CONCAT(function_areas, 'function_measurement_eval,') WHERE function_measurement_eval = 1;",
             "UPDATE onboarding_userextendedprofile SET function_areas = CONCAT(function_areas, 'function_stakeholder_engagement,')	WHERE function_stakeholder_engagement = 1;",
             "UPDATE onboarding_userextendedprofile SET function_areas = CONCAT(function_areas, 'function_human_resource,') WHERE function_human_resource = 1;",
             "UPDATE onboarding_userextendedprofile SET function_areas = CONCAT(function_areas, 'function_financial_management,') WHERE function_financial_management = 1;",
             "UPDATE onboarding_userextendedprofile SET function_areas = CONCAT(function_areas, 'function_fundraising,') WHERE function_fundraising = 1;",
             "UPDATE onboarding_userextendedprofile SET function_areas = CONCAT(function_areas, 'function_marketing_communication,') WHERE function_marketing_communication = 1;",
             "UPDATE onboarding_userextendedprofile SET function_areas = CONCAT(function_areas, 'function_system_tools') WHERE function_system_tools = 1;",
             "UPDATE onboarding_userextendedprofile SET function_areas = TRIM(TRAILING ',' FROM function_areas) WHERE function_areas <> '';",

             "UPDATE onboarding_userextendedprofile SET interests = CONCAT(interests, 'interest_strategy_planning,') WHERE interest_strategy_planning = 1;",
             "UPDATE onboarding_userextendedprofile SET interests = CONCAT(interests, 'interest_leadership_governance,') WHERE interest_leadership_governance = 1;",
             "UPDATE onboarding_userextendedprofile SET interests = CONCAT(interests, 'interest_program_design,') WHERE interest_program_design = 1;",
             "UPDATE onboarding_userextendedprofile SET interests = CONCAT(interests, 'interest_measurement_eval,') WHERE interest_measurement_eval = 1;",
             "UPDATE onboarding_userextendedprofile SET interests = CONCAT(interests, 'interest_stakeholder_engagement,') WHERE interest_stakeholder_engagement = 1;",
             "UPDATE onboarding_userextendedprofile SET interests = CONCAT(interests, 'interest_human_resource,') WHERE interest_human_resource = 1;",
             "UPDATE onboarding_userextendedprofile SET interests = CONCAT(interests, 'interest_financial_management,') WHERE interest_financial_management = 1;",
             "UPDATE onboarding_userextendedprofile SET interests = CONCAT(interests, 'interest_fundraising,') WHERE interest_fundraising = 1;",
             "UPDATE onboarding_userextendedprofile SET interests = CONCAT(interests, 'interest_marketing_communication,') WHERE interest_marketing_communication = 1;",
             "UPDATE onboarding_userextendedprofile SET interests = CONCAT(interests, 'interest_system_tools') WHERE interest_system_tools = 1;",
             "UPDATE onboarding_userextendedprofile SET interests = TRIM(TRAILING ',' FROM interests) WHERE interests <> '';",

             "UPDATE onboarding_userextendedprofile SET learners_related = CONCAT(learners_related, 'learners_same_region,') WHERE learners_same_region = 1;",
             "UPDATE onboarding_userextendedprofile SET learners_related = CONCAT(learners_related, 'learners_similar_oe_interest,') WHERE learners_similar_oe_interest = 1;",
             "UPDATE onboarding_userextendedprofile SET learners_related = CONCAT(learners_related, 'learners_similar_org,') WHERE learners_similar_org = 1;",
             "UPDATE onboarding_userextendedprofile SET learners_related = CONCAT(learners_related, 'learners_diff_who_are_different') WHERE learners_diff_who_are_different = 1;",
             "UPDATE onboarding_userextendedprofile SET learners_related = TRIM(TRAILING ',' FROM learners_related) WHERE learners_related <> '';",

             "UPDATE onboarding_userextendedprofile SET goals = CONCAT(goals, 'goal_contribute_to_org,') WHERE goal_contribute_to_org = 1;",
             "UPDATE onboarding_userextendedprofile SET goals = CONCAT(goals, 'goal_gain_new_skill,') WHERE goal_gain_new_skill = 1;",
             "UPDATE onboarding_userextendedprofile SET goals = CONCAT(goals, 'goal_improve_job_prospect,') WHERE goal_improve_job_prospect = 1;",
             "UPDATE onboarding_userextendedprofile SET goals = CONCAT(goals, 'goal_relation_with_other') WHERE goal_relation_with_other = 1;",
             "UPDATE onboarding_userextendedprofile SET goals = TRIM(TRAILING ',' FROM goals) WHERE goals <> '';",

             """UPDATE onboarding_userextendedprofile SET hear_about_philanthropyu =
                CASE
                    WHEN hear_about_philanthropy = 'Other'
                    THEN
                        CASE
                            WHEN hear_about_philanthropy_other <> ''
                            THEN CONCAT('|', hear_about_philanthropy_other)
                            ELSE ''
                        END
                    ELSE
                    CASE
                        WHEN hear_about_philanthropy = 'A Philanthropy University Partner (Global Giving, +Acumen or another)'
                        THEN 'hear_about_philanthropy_partner,|'

                        WHEN hear_about_philanthropy = 'A Colleague From My Organization'
                        THEN 'hear_about_colleague_same_organization,|'

                        WHEN hear_about_philanthropy = 'A Friend Or Colleague (Not From My Organization)'
                        THEN 'hear_about_friend_new_organization,|'

                        WHEN hear_about_philanthropy = 'An Internet Search'
                        THEN 'hear_about_interest_search,|'

                        WHEN hear_about_philanthropy = 'A LinkedIn Advertisement'
                        THEN 'hear_about_linkedIn_advertisement,|'

                        WHEN hear_about_philanthropy = 'A Facebook Advertisement'
                        THEN 'hear_about_facebook_advertisement,|'

                        WHEN hear_about_philanthropy = 'Twitter (Not From A Colleague)'
                        THEN 'hear_about_twitter_not_colleague,|'
                    END
                END
                WHERE hear_about_philanthropy IS NOT NULL;
             """,

             "COMMIT;"]
        )
    ]
