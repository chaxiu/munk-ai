export interface paths {
    "/healthz": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Healthz */
        get: operations["healthz_healthz_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/apps": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Apps */
        get: operations["list_apps_v1_apps_get"];
        put?: never;
        /** Create App */
        post: operations["create_app_v1_apps_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/apps/{app_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get App */
        get: operations["get_app_v1_apps__app_id__get"];
        /** Update App */
        put: operations["update_app_v1_apps__app_id__put"];
        post?: never;
        /** Delete App */
        delete: operations["delete_app_v1_apps__app_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/apps/{app_id}/knowledge/candidates": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Candidates */
        get: operations["list_candidates_v1_apps__app_id__knowledge_candidates_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/apps/{app_id}/knowledge/candidates/{candidate_id}/approve": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Approve Candidate */
        post: operations["approve_candidate_v1_apps__app_id__knowledge_candidates__candidate_id__approve_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/apps/{app_id}/knowledge/candidates/{candidate_id}/reject": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Reject Candidate */
        post: operations["reject_candidate_v1_apps__app_id__knowledge_candidates__candidate_id__reject_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/apps/{app_id}/knowledge/cards": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Cards */
        get: operations["list_cards_v1_apps__app_id__knowledge_cards_get"];
        put?: never;
        /** Create Card */
        post: operations["create_card_v1_apps__app_id__knowledge_cards_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/apps/{app_id}/knowledge/cards/{card_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Card */
        get: operations["get_card_v1_apps__app_id__knowledge_cards__card_id__get"];
        /** Update Card */
        put: operations["update_card_v1_apps__app_id__knowledge_cards__card_id__put"];
        post?: never;
        /** Delete Card */
        delete: operations["delete_card_v1_apps__app_id__knowledge_cards__card_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/cloud/apps": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Cloud Apps */
        get: operations["list_cloud_apps_v1_cloud_apps_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/cloud/auth/login": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Start Cloud Login */
        post: operations["start_cloud_login_v1_cloud_auth_login_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/cloud/auth/logout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Logout Cloud Session */
        post: operations["logout_cloud_session_v1_cloud_auth_logout_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/cloud/auth/session": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Cloud Session */
        get: operations["get_cloud_session_v1_cloud_auth_session_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/cloud/auth/workspaces": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Cloud Workspaces */
        get: operations["list_cloud_workspaces_v1_cloud_auth_workspaces_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/cloud/links": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Cloud Links */
        get: operations["get_cloud_links_v1_cloud_links_get"];
        /** Put Cloud Link */
        put: operations["put_cloud_link_v1_cloud_links_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/cloud/links/active": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Put Cloud Link Active */
        put: operations["put_cloud_link_active_v1_cloud_links_active_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/cloud/links/{app_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Cloud Link */
        delete: operations["delete_cloud_link_v1_cloud_links__app_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/cloud/sync/publish": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Post Cloud Sync Publish */
        post: operations["post_cloud_sync_publish_v1_cloud_sync_publish_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/cloud/sync/pull": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Post Cloud Sync Pull */
        post: operations["post_cloud_sync_pull_v1_cloud_sync_pull_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/cloud/sync/push": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Post Cloud Sync Push */
        post: operations["post_cloud_sync_push_v1_cloud_sync_push_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/cloud/sync/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Cloud Sync Status */
        get: operations["get_cloud_sync_status_v1_cloud_sync_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/dashboard/summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Dashboard Summary */
        get: operations["dashboard_summary_v1_dashboard_summary_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/device-state": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Device State */
        get: operations["get_device_state_v1_device_state_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/device-unlock": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Unlock Device */
        post: operations["unlock_device_v1_device_unlock_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/devices": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Devices */
        get: operations["list_devices_v1_devices_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/devices/install": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Install App */
        post: operations["install_app_v1_devices_install_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/interactive/sessions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Interactive Session */
        post: operations["create_interactive_session_v1_interactive_sessions_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/interactive/sessions/{session_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Interactive Session */
        get: operations["get_interactive_session_v1_interactive_sessions__session_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/interactive/sessions/{session_id}/abort": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Abort Interactive Session */
        post: operations["abort_interactive_session_v1_interactive_sessions__session_id__abort_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/interactive/sessions/{session_id}/finalize": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Finalize Interactive Session */
        post: operations["finalize_interactive_session_v1_interactive_sessions__session_id__finalize_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/plan": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Plan */
        post: operations["plan_v1_plan_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/plans": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Plans */
        get: operations["list_plans_v1_plans_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/plans/cases": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Search Cases */
        get: operations["search_cases_v1_plans_cases_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/plans/{app_id}/{plan_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Plan */
        get: operations["get_plan_v1_plans__app_id___plan_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/plans/{app_id}/{plan_id}/cases": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Add Case */
        post: operations["add_case_v1_plans__app_id___plan_id__cases_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/plans/{app_id}/{plan_id}/cases/{case_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Case */
        get: operations["get_case_v1_plans__app_id___plan_id__cases__case_id__get"];
        /** Update Case */
        put: operations["update_case_v1_plans__app_id___plan_id__cases__case_id__put"];
        post?: never;
        /** Delete Case */
        delete: operations["delete_case_v1_plans__app_id___plan_id__cases__case_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/plans/{app_id}/{plan_id}/cases/{case_id}/replace": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Replace Case */
        put: operations["replace_case_v1_plans__app_id___plan_id__cases__case_id__replace_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/plans/{app_id}/{plan_id}/cases/{case_id}/rewrite-preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Rewrite Case Preview */
        post: operations["rewrite_case_preview_v1_plans__app_id___plan_id__cases__case_id__rewrite_preview_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/plans/{app_id}/{plan_id}/cases:reorder": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Reorder Cases */
        post: operations["reorder_cases_v1_plans__app_id___plan_id__cases_reorder_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/plans:import": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Import Plan */
        post: operations["import_plan_v1_plans_import_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/recordings": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Recording */
        post: operations["create_recording_v1_recordings_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/recordings/{recording_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Recording */
        get: operations["get_recording_v1_recordings__recording_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/recordings/{recording_id}/analysis": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Analyze Recording */
        get: operations["analyze_recording_v1_recordings__recording_id__analysis_get"];
        put?: never;
        /** Submit Recording Analysis */
        post: operations["submit_recording_analysis_v1_recordings__recording_id__analysis_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/recordings/{recording_id}/begin": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Begin Recording */
        post: operations["begin_recording_v1_recordings__recording_id__begin_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/recordings/{recording_id}/cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Cancel Recording */
        post: operations["cancel_recording_v1_recordings__recording_id__cancel_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/recordings/{recording_id}/events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Record Interaction */
        post: operations["record_interaction_v1_recordings__recording_id__events_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/recordings/{recording_id}/events/tap": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Observe Tap */
        post: operations["observe_tap_v1_recordings__recording_id__events_tap_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/recordings/{recording_id}/export-case": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Export Recording Case */
        post: operations["export_recording_case_v1_recordings__recording_id__export_case_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/recordings/{recording_id}/observations/{observation_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Recording Observation */
        get: operations["get_recording_observation_v1_recordings__recording_id__observations__observation_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/recordings/{recording_id}/replay-case": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Replay Recording Case */
        post: operations["replay_recording_case_v1_recordings__recording_id__replay_case_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/recordings/{recording_id}/stop": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Stop Recording */
        post: operations["stop_recording_v1_recordings__recording_id__stop_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/recordings/{recording_id}/timeline": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Recording Timeline */
        get: operations["get_recording_timeline_v1_recordings__recording_id__timeline_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/review": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Review */
        post: operations["review_v1_review_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/run/case": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Run Case */
        post: operations["run_case_v1_run_case_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/run/plan": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Run Plan */
        post: operations["run_plan_v1_run_plan_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/run/plans": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Run Plans */
        post: operations["run_plans_v1_run_plans_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/runs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Runs List */
        get: operations["runs_list_v1_runs_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/runs/{operation_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Runs Get */
        get: operations["runs_get_v1_runs__operation_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/runs/{operation_id}/artifacts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Runs Artifacts */
        get: operations["runs_artifacts_v1_runs__operation_id__artifacts_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/runs/{operation_id}/artifacts/{artifact_id}/children": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Runs Artifact Children */
        get: operations["runs_artifact_children_v1_runs__operation_id__artifacts__artifact_id__children_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/runs/{operation_id}/artifacts/{artifact_id}/children/{child_id}/content": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Runs Artifact Child Content */
        get: operations["runs_artifact_child_content_v1_runs__operation_id__artifacts__artifact_id__children__child_id__content_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/runs/{operation_id}/artifacts/{artifact_id}/content": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Runs Artifact Content */
        get: operations["runs_artifact_content_v1_runs__operation_id__artifacts__artifact_id__content_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/runs/{operation_id}/artifacts/{artifact_id}/download": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Runs Artifact Download */
        get: operations["runs_artifact_download_v1_runs__operation_id__artifacts__artifact_id__download_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/runs/{operation_id}/cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Runs Cancel */
        post: operations["runs_cancel_v1_runs__operation_id__cancel_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/runs/{operation_id}/children": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Runs Children */
        get: operations["runs_children_v1_runs__operation_id__children_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/runs/{operation_id}/events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Runs Events */
        get: operations["runs_events_v1_runs__operation_id__events_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/runs/{operation_id}/reproduce": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Runs Reproduce */
        post: operations["runs_reproduce_v1_runs__operation_id__reproduce_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/schedules": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Schedules */
        get: operations["list_schedules_v1_schedules_get"];
        put?: never;
        /** Create Schedule */
        post: operations["create_schedule_v1_schedules_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/schedules/{schedule_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Schedule */
        get: operations["get_schedule_v1_schedules__schedule_id__get"];
        /** Update Schedule */
        put: operations["update_schedule_v1_schedules__schedule_id__put"];
        post?: never;
        /** Delete Schedule */
        delete: operations["delete_schedule_v1_schedules__schedule_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/schedules/{schedule_id}/runs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Schedule Runs */
        get: operations["list_schedule_runs_v1_schedules__schedule_id__runs_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/schedules/{schedule_id}:disable": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Disable Schedule */
        post: operations["disable_schedule_v1_schedules__schedule_id__disable_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/schedules/{schedule_id}:enable": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Enable Schedule */
        post: operations["enable_schedule_v1_schedules__schedule_id__enable_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/settings/config": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Settings Config */
        get: operations["get_settings_config_v1_settings_config_get"];
        /** Update Settings Config */
        put: operations["update_settings_config_v1_settings_config_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/verify/change": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Verify Change */
        post: operations["verify_change_v1_verify_change_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/verify/readiness": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Verify Readiness */
        get: operations["verify_readiness_v1_verify_readiness_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/verify/readiness/probe": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Verify Readiness Probe */
        post: operations["verify_readiness_probe_v1_verify_readiness_probe_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AgentConfigEditor */
        AgentConfigEditor: {
            /**
             * Enabled
             * @default false
             */
            enabled: boolean;
            gemini?: components["schemas"]["GeminiSectionEditor"];
            openai_compatible?: components["schemas"]["OpenAICompatibleSectionEditor"];
            /** Provider */
            provider?: ("openai_compatible" | "gemini") | null;
        };
        /** AgentRuntimeLifecycleEventPayload */
        AgentRuntimeLifecycleEventPayload: {
            /** Agent Role */
            agent_role: string;
            /** Event Timestamp */
            event_timestamp?: string | null;
            /** Lifecycle State */
            lifecycle_state: string;
            /** Runner Event Type */
            runner_event_type?: string | null;
            /** Timestamp */
            timestamp?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** AiGuidance */
        AiGuidance: {
            /** Disambiguation Rules */
            disambiguation_rules?: string[];
            /** Interaction Hints */
            interaction_hints?: string[];
            /** Judge Hints */
            judge_hints?: string[];
            /** Objective Clarifications */
            objective_clarifications?: string[];
            /** Preflight Checks */
            preflight_checks?: string[];
            /** Recovery Hints */
            recovery_hints?: string[];
        };
        /** AndroidAppIdentity */
        AndroidAppIdentity: {
            /** Activity Name */
            activity_name?: string | null;
            /** Package Name */
            package_name: string;
        };
        /** ApiError */
        ApiError: {
            /** Code */
            code: string;
            /** Details */
            details?: {
                [key: string]: unknown;
            } | null;
            /** Message */
            message: string;
        };
        /** AppDetailData */
        AppDetailData: {
            /** App Knowledge Content */
            app_knowledge_content?: string | null;
            /**
             * App Knowledge Exists
             * @default false
             */
            app_knowledge_exists: boolean;
            app_target: components["schemas"]["AppTarget"];
            /**
             * Case Count
             * @default 0
             */
            case_count: number;
            /** Introduction Markdown */
            introduction_markdown: string;
            /**
             * Plan Count
             * @default 0
             */
            plan_count: number;
            profile: components["schemas"]["AppProfile"];
        };
        /** AppListData */
        AppListData: {
            /** Items */
            items?: components["schemas"]["AppListItemData"][];
        };
        /** AppListItemData */
        AppListItemData: {
            /** App Id */
            app_id: string;
            /** App Name */
            app_name?: string | null;
            /**
             * Case Count
             * @default 0
             */
            case_count: number;
            /** Entry Identity */
            entry_identity?: string | null;
            /**
             * Introduction Exists
             * @default true
             */
            introduction_exists: boolean;
            /**
             * Plan Count
             * @default 0
             */
            plan_count: number;
            /** Platform */
            platform: string;
        };
        /** AppProfile */
        AppProfile: {
            android?: components["schemas"]["AndroidAppIdentity"] | null;
            /** App Id */
            app_id: string;
            /** App Introduction Ref */
            app_introduction_ref?: string;
            /** App Knowledge Ref */
            app_knowledge_ref?: string;
            /** App Name */
            app_name?: string | null;
            ios?: components["schemas"]["IOSAppIdentity"] | null;
            /**
             * Platform
             * @enum {string}
             */
            platform: "android" | "ios" | "web";
            web?: components["schemas"]["WebAppIdentity"] | null;
        };
        /** AppTarget */
        AppTarget: {
            android?: components["schemas"]["AndroidAppIdentity"] | null;
            /** App Id */
            app_id: string;
            /** Entry Identity */
            entry_identity?: string | null;
            ios?: components["schemas"]["IOSAppIdentity"] | null;
            /** Launch Context */
            launch_context?: {
                [key: string]: string;
            };
            /**
             * Platform
             * @enum {string}
             */
            platform: "android" | "ios" | "web";
            web?: components["schemas"]["WebAppIdentity"] | null;
        };
        /** AppUpsertProfile */
        AppUpsertProfile: {
            android?: components["schemas"]["AndroidAppIdentity"] | null;
            /** App Id */
            app_id: string;
            /** App Introduction Ref */
            app_introduction_ref?: string;
            /** App Knowledge Ref */
            app_knowledge_ref?: string;
            /** App Name */
            app_name: string;
            ios?: components["schemas"]["IOSAppIdentity"] | null;
            /**
             * Platform
             * @enum {string}
             */
            platform: "android" | "ios" | "web";
            web?: components["schemas"]["WebAppIdentity"] | null;
        };
        /** AppUpsertRequest */
        AppUpsertRequest: {
            /** App Knowledge Content */
            app_knowledge_content?: string | null;
            /** App Knowledge File Name */
            app_knowledge_file_name?: string | null;
            /** Introduction Markdown */
            introduction_markdown: string;
            profile: components["schemas"]["AppUpsertProfile"];
        };
        /** ArtifactSchemaVersions */
        ArtifactSchemaVersions: {
            /** Operation Diagnostics */
            operation_diagnostics?: string | null;
            /** Plan Repair Report */
            plan_repair_report?: string | null;
            /** Review Orchestration */
            review_orchestration?: string | null;
            /** Review Result */
            review_result?: string | null;
        };
        /** AssertionKnowledgeCandidateDraft */
        AssertionKnowledgeCandidateDraft: {
            /** App Id */
            app_id: string;
            /** Card Id */
            card_id?: string | null;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            card_type: "assertion";
            /** Confidence */
            confidence: number;
            payload: components["schemas"]["AssertionPayload"];
            source: components["schemas"]["KnowledgeSource"];
            /** Title */
            title: string;
        };
        /** AssertionKnowledgeCard */
        AssertionKnowledgeCard: {
            /** App Id */
            app_id: string;
            /** Card Id */
            card_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            card_type: "assertion";
            /** Confidence */
            confidence: number;
            payload: components["schemas"]["AssertionPayload"];
            source: components["schemas"]["KnowledgeSource"];
            /**
             * Status
             * @enum {string}
             */
            status: "active" | "deprecated" | "archived";
            /** Title */
            title: string;
            /** Updated At */
            updated_at: string;
        };
        /** AssertionKnowledgeCardInput */
        AssertionKnowledgeCardInput: {
            /** App Id */
            app_id: string;
            /** Card Id */
            card_id?: string | null;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            card_type: "assertion";
            /** Confidence */
            confidence: number;
            payload: components["schemas"]["AssertionPayload"];
            source: components["schemas"]["KnowledgeSource"];
            /**
             * Status
             * @default active
             * @enum {string}
             */
            status: "active" | "deprecated" | "archived";
            /** Title */
            title: string;
        };
        /** AssertionPayload */
        AssertionPayload: {
            /** Failure Signals */
            failure_signals?: string[];
            /** Success Signals */
            success_signals?: string[];
            /** Verdict Hint */
            verdict_hint?: string | null;
            /** When */
            when: string;
        };
        /** AttemptTokenUsageData */
        AttemptTokenUsageData: {
            /** Attempt Index */
            attempt_index: number;
            judge_usage?: components["schemas"]["TokenUsageData"] | null;
            runner_usage?: components["schemas"]["TokenUsageData"] | null;
            total_usage?: components["schemas"]["TokenUsageData"] | null;
        };
        /** BackForwardingPayload */
        BackForwardingPayload: Record<string, never>;
        /** BatchChildFinishedEventPayload */
        BatchChildFinishedEventPayload: {
            /** Case Id */
            case_id?: string | null;
            /** Created At */
            created_at: string;
            /** Error Code */
            error_code?: string | null;
            /** Error Message */
            error_message?: string | null;
            /** Finished At */
            finished_at?: string | null;
            /** Operation Id */
            operation_id: string;
            /** Plan Id */
            plan_id?: string | null;
            /** Position Index */
            position_index?: number | null;
            /** Position Label */
            position_label?: string | null;
            /** Started At */
            started_at?: string | null;
            /** Status */
            status: string;
            /** Title */
            title: string;
            token_usage?: components["schemas"]["TokenUsage"] | null;
            /** Verification Verdict */
            verification_verdict?: ("passed" | "failed" | "inconclusive") | null;
        } & {
            [key: string]: unknown;
        };
        /** BatchChildStartedEventPayload */
        BatchChildStartedEventPayload: {
            /** Case Id */
            case_id?: string | null;
            /** Operation Id */
            operation_id: string;
            /** Parent Operation Id */
            parent_operation_id?: string | null;
            /** Plan Id */
            plan_id?: string | null;
            /** Position Label */
            position_label?: string | null;
            /** Title */
            title: string;
        } & {
            [key: string]: unknown;
        };
        /** BatchFinishedEventPayload */
        BatchFinishedEventPayload: {
            /** Completed Children */
            completed_children: number;
            /**
             * Stopped Early
             * @default false
             */
            stopped_early: boolean;
            /** Total Children */
            total_children: number;
            /** Verification Verdict */
            verification_verdict?: ("passed" | "failed" | "inconclusive") | null;
        } & {
            [key: string]: unknown;
        };
        /** BatchRunAggregateData */
        BatchRunAggregateData: {
            /**
             * Cancelled Children
             * @default 0
             */
            cancelled_children: number;
            /**
             * Completed Children
             * @default 0
             */
            completed_children: number;
            /** Current Child Case Id */
            current_child_case_id?: string | null;
            /** Current Child Operation Id */
            current_child_operation_id?: string | null;
            /** Current Child Plan Id */
            current_child_plan_id?: string | null;
            /** Current Child Title */
            current_child_title?: string | null;
            /**
             * Failed Children
             * @default 0
             */
            failed_children: number;
            /**
             * Interrupted Children
             * @default 0
             */
            interrupted_children: number;
            /**
             * Queued Children
             * @default 0
             */
            queued_children: number;
            /**
             * Running Children
             * @default 0
             */
            running_children: number;
            /**
             * Succeeded Children
             * @default 0
             */
            succeeded_children: number;
            token_usage?: components["schemas"]["TokenUsageData"] | null;
            /**
             * Total Children
             * @default 0
             */
            total_children: number;
        };
        /** BatchStartedEventPayload */
        BatchStartedEventPayload: {
            /** App Id */
            app_id: string;
            /** Device Ref */
            device_ref?: string | null;
            /** Plan Ids */
            plan_ids?: string[] | null;
            /** Total Children */
            total_children?: number | null;
        } & {
            [key: string]: unknown;
        };
        /** BatchStoppedEarlyEventPayload */
        BatchStoppedEarlyEventPayload: {
            /** Operation Id */
            operation_id: string;
            /** Plan Id */
            plan_id: string;
        } & {
            [key: string]: unknown;
        };
        /** CancelOperationData */
        CancelOperationData: {
            /** Cancel Requested */
            cancel_requested: boolean;
            /** Operation Id */
            operation_id: string;
            /** Status */
            status: string;
        };
        /** CaseBriefData */
        CaseBriefData: {
            /** Case Id */
            case_id: string;
            /** Intent */
            intent: string;
            /** Is Core Case */
            is_core_case: boolean;
            /** Runner Goal */
            runner_goal: string;
            /** Start Mode */
            start_mode: string;
            /** Start Page Id */
            start_page_id?: string | null;
            /** Title */
            title: string;
        };
        /** CaseBudget */
        CaseBudget: {
            /** Max Seconds */
            max_seconds?: number | null;
            /** Max Steps */
            max_steps?: number | null;
        };
        /** CaseBudgetRequest */
        CaseBudgetRequest: {
            /** Max Seconds */
            max_seconds?: number | null;
            /** Max Steps */
            max_steps?: number | null;
        };
        /** CaseDeleteData */
        CaseDeleteData: {
            /** App Id */
            app_id: string;
            /**
             * Case Count
             * @default 0
             */
            case_count: number;
            /** Case Id */
            case_id: string;
            /** Plan Id */
            plan_id: string;
        };
        /** CaseDetailData */
        CaseDetailData: {
            ai_guidance?: components["schemas"]["AiGuidance"] | null;
            /** App Id */
            app_id: string;
            /** Case Id */
            case_id: string;
            /** Expected */
            expected?: string[];
            /** Intent */
            intent: string;
            /** Is Core Case */
            is_core_case: boolean;
            latest_optimize?: components["schemas"]["LatestOptimizeOperationData"] | null;
            /** Max Seconds */
            max_seconds?: number | null;
            /** Max Steps */
            max_steps?: number | null;
            /** Plan Id */
            plan_id: string;
            /** Plan Source */
            plan_source: string;
            /** Plan Version */
            plan_version: string;
            /** Post Action */
            post_action?: string[];
            /** Preconditions */
            preconditions?: string[];
            /** Procedure */
            procedure?: string[];
            /** Runner Goal */
            runner_goal: string;
            /** Setup */
            setup?: (components["schemas"]["HttpSetupStep"] | components["schemas"]["CommandSetupStep"])[];
            /** Start Mode */
            start_mode: string;
            /** Start Page Id */
            start_page_id?: string | null;
            /** Title */
            title: string;
        };
        /** CaseExecutionAttempt */
        CaseExecutionAttempt: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            };
            /** Attempt Index */
            attempt_index: number;
            /** Confidence */
            confidence?: number | null;
            /** Decision */
            decision?: {
                [key: string]: unknown;
            } | null;
            /** Evidence */
            evidence?: (components["schemas"]["JudgeExecutionEvidence"] | components["schemas"]["JudgeEventEvidence"] | components["schemas"]["JudgeDecisionTraceEvidence"] | components["schemas"]["JudgeRunnerHistoryEvidence"] | components["schemas"]["JudgeRunnerMemoryEvidence"] | components["schemas"]["JudgeRunnerIssueEvidence"] | components["schemas"]["JudgeRuntimeErrorLogEvidence"] | components["schemas"]["JudgeScreenFrameEvidence"] | components["schemas"]["JudgeScreenDiffEvidence"] | components["schemas"]["JudgeScreenshotEvidence"])[];
            execution: components["schemas"]["ExecutionOutcome"];
            /** Failure Hypothesis */
            failure_hypothesis?: string | null;
            /** Judge Reason */
            judge_reason?: string | null;
            judge_usage?: components["schemas"]["TokenUsage"] | null;
            /** Missing Evidence */
            missing_evidence?: string[];
            /** Retry Handoff Message */
            retry_handoff_message?: string | null;
            /** Retry Reason */
            retry_reason?: string | null;
            /**
             * Runner Run Dir
             * Format: path
             */
            runner_run_dir: string;
            runner_usage?: components["schemas"]["TokenUsage"] | null;
            /** Summary */
            summary?: string | null;
            /** Supplemental Context */
            supplemental_context?: string[];
            /** Supporting Evidence Ids */
            supporting_evidence_ids?: string[];
            total_usage?: components["schemas"]["TokenUsage"] | null;
            /**
             * Verdict
             * @enum {string}
             */
            verdict: "passed" | "failed" | "inconclusive";
        };
        /** CaseRewritePreviewData */
        CaseRewritePreviewData: {
            case: components["schemas"]["TestCasePayload"];
            /** Source Prompt */
            source_prompt: string;
        };
        /** CaseRewritePreviewRequest */
        CaseRewritePreviewRequest: {
            /** Prompt */
            prompt: string;
        };
        /** CaseRunArtifactSummaryData */
        CaseRunArtifactSummaryData: {
            /** Case Id */
            case_id: string;
            /** Execution Status */
            execution_status: string;
            /** Operation Id */
            operation_id?: string | null;
            /** Run Dir */
            run_dir: string;
            /** Title */
            title: string;
            token_usage?: components["schemas"]["TokenUsageData"] | null;
            /** Verdict */
            verdict: string;
        };
        /** CaseSearchData */
        CaseSearchData: {
            /** Items */
            items?: components["schemas"]["CaseSearchItemData"][];
            /**
             * Limit
             * @default 20
             */
            limit: number;
            /**
             * Offset
             * @default 0
             */
            offset: number;
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** CaseSearchItemData */
        CaseSearchItemData: {
            /** App Id */
            app_id: string;
            /** Case Id */
            case_id: string;
            /** Intent */
            intent: string;
            /** Is Core Case */
            is_core_case: boolean;
            /** Max Seconds */
            max_seconds?: number | null;
            /** Max Steps */
            max_steps?: number | null;
            /** Ordinal */
            ordinal: number;
            /** Plan Id */
            plan_id: string;
            /** Plan Name */
            plan_name?: string | null;
            /** Runner Goal */
            runner_goal: string;
            /** Start Mode */
            start_mode: string;
            /** Start Page Id */
            start_page_id?: string | null;
            /** Title */
            title: string;
        };
        /** CaseStartState */
        CaseStartState: {
            /**
             * Mode
             * @default reset
             * @enum {string}
             */
            mode: "reset" | "resume";
            /**
             * Page Id
             * @description Optional semantic app page identifier. Resolution depends on app-specific navigation support and is not validated against a central registry.
             */
            page_id?: string | null;
        };
        /** CaseStartStateRequest */
        CaseStartStateRequest: {
            /**
             * Mode
             * @default reset
             * @enum {string}
             */
            mode: "reset" | "resume";
            /** Page Id */
            page_id?: string | null;
        };
        /** CaseUpdateRequest */
        CaseUpdateRequest: {
            /** Expected */
            expected?: string[] | null;
            /** Intent */
            intent?: string | null;
            /** Post Action */
            post_action?: string[] | null;
            /** Preconditions */
            preconditions?: string[] | null;
            /** Procedure */
            procedure?: string[] | null;
            /** Runner Goal */
            runner_goal?: string | null;
            /** Start Mode */
            start_mode?: ("reset" | "resume") | null;
            /** Start Page Id */
            start_page_id?: string | null;
        };
        /** CaseUpsertRequest */
        CaseUpsertRequest: {
            case: components["schemas"]["TestCasePayload"];
        };
        /** ChangeVerificationCasesReadyPayload */
        ChangeVerificationCasesReadyPayload: {
            /** Manual Case Count */
            manual_case_count: number;
            /** Planner Case Count */
            planner_case_count: number;
            /** Review Hint Enabled */
            review_hint_enabled: boolean;
            /** Review Required Case Count */
            review_required_case_count: number;
        };
        /** ChangeVerificationPlanSavedPayload */
        ChangeVerificationPlanSavedPayload: {
            /** App Id */
            app_id: string;
            /** Case Count */
            case_count: number;
            /** Plan Id */
            plan_id: string;
            /** Plan Path */
            plan_path: string;
            planning_usage?: components["schemas"]["TokenUsage"] | null;
            /** Snapshot Path */
            snapshot_path: string;
        };
        /** ChangeVerificationReviewContractLoadedPayload */
        ChangeVerificationReviewContractLoadedPayload: {
            /** App Id */
            app_id: string;
            /** Review Hint Enabled */
            review_hint_enabled: boolean;
            /** Review Required Case Count */
            review_required_case_count: number;
        };
        /** CloudAppSummaryData */
        CloudAppSummaryData: {
            /** App Id */
            app_id: string;
            /** App Name */
            app_name?: string | null;
            /** Content Hash */
            content_hash?: string | null;
            /** Platform */
            platform: string;
            /**
             * Revision
             * @default 0
             */
            revision: number;
            /** Updated At */
            updated_at?: string | null;
        };
        /** CloudAppsData */
        CloudAppsData: {
            /** Apps */
            apps?: components["schemas"]["CloudAppSummaryData"][];
            /** Workspace Id */
            workspace_id: string;
        };
        /** CloudLinkActiveRequest */
        CloudLinkActiveRequest: {
            /** App Id */
            app_id: string;
        };
        /** CloudLinkData */
        CloudLinkData: {
            /** App Id */
            app_id: string;
            /**
             * Bound At
             * Format: date-time
             */
            bound_at: string;
            /** Role */
            role?: string | null;
            /** Workspace Id */
            workspace_id: string;
            /** Workspace Name */
            workspace_name?: string | null;
        };
        /** CloudLinkItemData */
        CloudLinkItemData: {
            /** App Id */
            app_id: string;
            /** Base Revision */
            base_revision?: number | null;
            /**
             * Bound At
             * Format: date-time
             */
            bound_at: string;
            /**
             * Dirty
             * @default false
             */
            dirty: boolean;
            /** Last Action */
            last_action?: ("pull" | "push" | "force_push") | null;
            /** Last Synced At */
            last_synced_at?: string | null;
            /** Role */
            role?: string | null;
            /** Workspace Id */
            workspace_id: string;
            /** Workspace Name */
            workspace_name?: string | null;
        };
        /** CloudLinkUpsertRequest */
        CloudLinkUpsertRequest: {
            /** App Id */
            app_id: string;
            /** Role */
            role?: string | null;
            /** Workspace Id */
            workspace_id: string;
            /** Workspace Name */
            workspace_name?: string | null;
        };
        /** CloudLinksData */
        CloudLinksData: {
            /** Active App Id */
            active_app_id?: string | null;
            /** Items */
            items?: components["schemas"]["CloudLinkItemData"][];
        };
        /** CloudLoginStartData */
        CloudLoginStartData: {
            /** Authorize Url */
            authorize_url: string;
            /** Redirect Uri */
            redirect_uri: string;
            /** State */
            state: string;
        };
        /** CloudSessionSummaryData */
        CloudSessionSummaryData: {
            /**
             * Authenticated
             * @default false
             */
            authenticated: boolean;
            /**
             * Can Refresh
             * @default false
             */
            can_refresh: boolean;
            /** Cloud Base Url */
            cloud_base_url?: string | null;
            /** Expires At */
            expires_at?: string | null;
            user?: components["schemas"]["CloudUserSummaryData"] | null;
        };
        /** CloudSyncPublishRequest */
        CloudSyncPublishRequest: {
            /** App Id */
            app_id: string;
            /** Workspace Id */
            workspace_id: string;
            /** Workspace Name */
            workspace_name?: string | null;
        };
        /** CloudSyncPublishResultData */
        CloudSyncPublishResultData: {
            /**
             * Action
             * @default push
             * @enum {string}
             */
            action: "push" | "force_push";
            /** App Id */
            app_id: string;
            /** Content Hash */
            content_hash?: string | null;
            /**
             * Forced
             * @default false
             */
            forced: boolean;
            /** Revision */
            revision: number;
            /**
             * Shell Created
             * @default false
             */
            shell_created: boolean;
            /** Workspace Id */
            workspace_id: string;
        };
        /** CloudSyncPullRequest */
        CloudSyncPullRequest: {
            /** App Id */
            app_id?: string | null;
            /**
             * Force
             * @default false
             */
            force: boolean;
        };
        /** CloudSyncPullResultData */
        CloudSyncPullResultData: {
            /** App Id */
            app_id: string;
            /** Content Hash */
            content_hash?: string | null;
            /**
             * Dirty
             * @default false
             */
            dirty: boolean;
            /**
             * Forced
             * @default false
             */
            forced: boolean;
            /**
             * Plans Deleted
             * @default 0
             */
            plans_deleted: number;
            /**
             * Plans Written
             * @default 0
             */
            plans_written: number;
            /** Revision */
            revision: number;
            /** Workspace Id */
            workspace_id: string;
        };
        /** CloudSyncPushRequest */
        CloudSyncPushRequest: {
            /** App Id */
            app_id?: string | null;
            /**
             * Force
             * @default false
             */
            force: boolean;
        };
        /** CloudSyncPushResultData */
        CloudSyncPushResultData: {
            /**
             * Action
             * @default push
             * @enum {string}
             */
            action: "push" | "force_push";
            /** App Id */
            app_id: string;
            /** Content Hash */
            content_hash?: string | null;
            /**
             * Forced
             * @default false
             */
            forced: boolean;
            /** Revision */
            revision: number;
            /** Workspace Id */
            workspace_id: string;
        };
        /** CloudSyncStatusData */
        CloudSyncStatusData: {
            /** App Id */
            app_id: string;
            /** Base Revision */
            base_revision?: number | null;
            /**
             * Bound
             * @default false
             */
            bound: boolean;
            /**
             * Can Force Push
             * @default false
             */
            can_force_push: boolean;
            /**
             * Can Pull
             * @default true
             */
            can_pull: boolean;
            /**
             * Can Push
             * @default false
             */
            can_push: boolean;
            /** Content Hash */
            content_hash?: string | null;
            /**
             * Dirty
             * @default false
             */
            dirty: boolean;
            /** Last Action */
            last_action?: ("pull" | "push" | "force_push") | null;
            /** Last Synced At */
            last_synced_at?: string | null;
            /** Local Content Hash */
            local_content_hash?: string | null;
            /**
             * Revision
             * @default 0
             */
            revision: number;
            /** Role */
            role: string;
            /** Workspace Id */
            workspace_id: string;
        };
        /** CloudUserSummaryData */
        CloudUserSummaryData: {
            /** Avatar Url */
            avatar_url?: string | null;
            /** Display Name */
            display_name?: string | null;
            /** Email */
            email?: string | null;
            /** Id */
            id: string;
        };
        /** CloudWorkspaceSummaryData */
        CloudWorkspaceSummaryData: {
            /** Id */
            id: string;
            /** Name */
            name: string;
            /** Role */
            role: string;
            /** Slug */
            slug: string;
        };
        /** CloudWorkspacesData */
        CloudWorkspacesData: {
            /** Workspaces */
            workspaces?: components["schemas"]["CloudWorkspaceSummaryData"][];
        };
        /** CommandSetupStep */
        CommandSetupStep: {
            /** Args */
            args?: string[];
            /** Exec */
            exec: string;
            /**
             * Expected Exit Code
             * @default 0
             */
            expected_exit_code: number;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "command";
        };
        /** ContextPrepareDeviceReadyEventPayload */
        ContextPrepareDeviceReadyEventPayload: {
            /** Agent Role */
            agent_role: string;
            /** Device Ref */
            device_ref?: string | null;
            /** Event Timestamp */
            event_timestamp?: string | null;
            /** Lifecycle State */
            lifecycle_state: string;
            /** Platform */
            platform?: string | null;
            /** Runner Event Type */
            runner_event_type?: string | null;
            /** Timestamp */
            timestamp?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** ContextPrepareFailedEventPayload */
        ContextPrepareFailedEventPayload: {
            /** Agent Role */
            agent_role: string;
            /** Error Message */
            error_message?: string | null;
            /** Error Type */
            error_type?: string | null;
            /** Event Timestamp */
            event_timestamp?: string | null;
            /** Failed Phase */
            failed_phase?: string | null;
            /** Lifecycle State */
            lifecycle_state: string;
            /** Runner Event Type */
            runner_event_type?: string | null;
            /** Step Index */
            step_index?: number | null;
            /** Timestamp */
            timestamp?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** ContextPrepareParamsResolvedEventPayload */
        ContextPrepareParamsResolvedEventPayload: {
            /** Agent Role */
            agent_role: string;
            /** Device Ref */
            device_ref?: string | null;
            /** Event Timestamp */
            event_timestamp?: string | null;
            /** Initial Ready Timeout Sec */
            initial_ready_timeout_sec?: number | null;
            /** Interval */
            interval?: number | null;
            /** Lifecycle State */
            lifecycle_state: string;
            /** Max Seconds */
            max_seconds?: number | null;
            /** Max Side */
            max_side?: number | null;
            /** Max Steps */
            max_steps?: number | null;
            /** Runner Event Type */
            runner_event_type?: string | null;
            /** Settle Delay Sec */
            settle_delay_sec?: number | null;
            /** Settle Mode */
            settle_mode?: string | null;
            /** Settle Ocr Only */
            settle_ocr_only?: boolean | null;
            /** Settle Ratio Threshold */
            settle_ratio_threshold?: number | null;
            /** Settle Timeout */
            settle_timeout?: number | null;
            /** Timestamp */
            timestamp?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** ContextPreparePerceptionReadyEventPayload */
        ContextPreparePerceptionReadyEventPayload: {
            /** Agent Role */
            agent_role: string;
            /** Event Timestamp */
            event_timestamp?: string | null;
            /** Icon Conf */
            icon_conf?: number | null;
            /** Lifecycle State */
            lifecycle_state: string;
            /** Max Side */
            max_side?: number | null;
            /** Runner Event Type */
            runner_event_type?: string | null;
            /** Timestamp */
            timestamp?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** ContextPrepareSetupReadyEventPayload */
        ContextPrepareSetupReadyEventPayload: {
            /** Agent Role */
            agent_role: string;
            /** Duration Ms */
            duration_ms?: number | null;
            /** Event Timestamp */
            event_timestamp?: string | null;
            /** Lifecycle State */
            lifecycle_state: string;
            /** Runner Event Type */
            runner_event_type?: string | null;
            /** Step Count */
            step_count?: number | null;
            /** Timestamp */
            timestamp?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** ContextPrepareSetupStartedEventPayload */
        ContextPrepareSetupStartedEventPayload: {
            /** Agent Role */
            agent_role: string;
            /** Event Timestamp */
            event_timestamp?: string | null;
            /** Lifecycle State */
            lifecycle_state: string;
            /** Runner Event Type */
            runner_event_type?: string | null;
            /** Step Count */
            step_count?: number | null;
            /** Timestamp */
            timestamp?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** ContextPrepareSetupStepEventPayload */
        ContextPrepareSetupStepEventPayload: {
            /** Agent Role */
            agent_role: string;
            /** Args */
            args?: string[] | null;
            /** Base */
            base?: string | null;
            /** Duration Ms */
            duration_ms?: number | null;
            /** Error Message */
            error_message?: string | null;
            /** Event Timestamp */
            event_timestamp?: string | null;
            /** Exec */
            exec?: string | null;
            /** Exit Code */
            exit_code?: number | null;
            /** Expected Exit Code */
            expected_exit_code?: number | null;
            /** Expected Status */
            expected_status?: number[] | null;
            /** Lifecycle State */
            lifecycle_state: string;
            /** Method */
            method?: string | null;
            /** Outcome */
            outcome?: string | null;
            /** Path */
            path?: string | null;
            /** Request Body */
            request_body?: unknown | null;
            /** Request Url */
            request_url?: string | null;
            /** Response Body */
            response_body?: string | null;
            /** Runner Event Type */
            runner_event_type?: string | null;
            /** Status Code */
            status_code?: number | null;
            /** Stderr Tail */
            stderr_tail?: string | null;
            /** Stdout Tail */
            stdout_tail?: string | null;
            /** Step Index */
            step_index?: number | null;
            /** Step Kind */
            step_kind?: string | null;
            /** Step Total */
            step_total?: number | null;
            /** Timestamp */
            timestamp?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** ContextPrepareStartStateReadyEventPayload */
        ContextPrepareStartStateReadyEventPayload: {
            /** Agent Role */
            agent_role: string;
            /** Duration Ms */
            duration_ms?: number | null;
            /** Event Timestamp */
            event_timestamp?: string | null;
            /** Lifecycle State */
            lifecycle_state: string;
            /** Runner Event Type */
            runner_event_type?: string | null;
            /** Step Count */
            step_count?: number | null;
            /** Timestamp */
            timestamp?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** ContextPrepareStartStateStartedEventPayload */
        ContextPrepareStartStateStartedEventPayload: {
            /** Agent Role */
            agent_role: string;
            /** Event Timestamp */
            event_timestamp?: string | null;
            /** Lifecycle State */
            lifecycle_state: string;
            /** Runner Event Type */
            runner_event_type?: string | null;
            /** Step Count */
            step_count?: number | null;
            /** Timestamp */
            timestamp?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** ContextPrepareStartStateStepEventPayload */
        ContextPrepareStartStateStepEventPayload: {
            /** Agent Role */
            agent_role: string;
            /** App Id */
            app_id?: string | null;
            /** Duration Ms */
            duration_ms?: number | null;
            /** Entry Identity */
            entry_identity?: string | null;
            /** Error Message */
            error_message?: string | null;
            /** Event Timestamp */
            event_timestamp?: string | null;
            /** Lifecycle State */
            lifecycle_state: string;
            /** Outcome */
            outcome?: string | null;
            /** Page Id */
            page_id?: string | null;
            /** Runner Event Type */
            runner_event_type?: string | null;
            /** Skip Reason */
            skip_reason?: string | null;
            /** Start Mode */
            start_mode?: string | null;
            /** Step Index */
            step_index?: number | null;
            /** Step Kind */
            step_kind?: string | null;
            /** Step Total */
            step_total?: number | null;
            /** Timestamp */
            timestamp?: string | null;
            /** Was Locked */
            was_locked?: boolean | null;
        } & {
            [key: string]: unknown;
        };
        /** CreateInteractiveSessionRequest */
        CreateInteractiveSessionRequest: {
            /** @description Application target to bind the interactive session to. */
            app_target: components["schemas"]["AppTarget"];
            /**
             * Config Path
             * @description Optional path to a Munk config file; otherwise workspace/profile discovery applies.
             */
            config_path?: string | null;
            /**
             * Device Ref
             * @description Optional device reference to claim for the interactive session.
             */
            device_ref?: string | null;
        };
        /** CreateRecordingRequest */
        CreateRecordingRequest: {
            app_target: components["schemas"]["AppTarget"];
            /** Case Id */
            case_id?: string | null;
            /** Device Ref */
            device_ref?: string | null;
        };
        /** DashboardSummaryData */
        DashboardSummaryData: {
            /**
             * Case Count
             * @default 0
             */
            case_count: number;
            /**
             * Plan Count
             * @default 0
             */
            plan_count: number;
            /**
             * Recent Run Count
             * @default 0
             */
            recent_run_count: number;
        };
        /** DataKnowledgeCandidateDraft */
        DataKnowledgeCandidateDraft: {
            /** App Id */
            app_id: string;
            /** Card Id */
            card_id?: string | null;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            card_type: "data";
            /** Confidence */
            confidence: number;
            payload: components["schemas"]["DataPayload"];
            source: components["schemas"]["KnowledgeSource"];
            /** Title */
            title: string;
        };
        /** DataKnowledgeCard */
        DataKnowledgeCard: {
            /** App Id */
            app_id: string;
            /** Card Id */
            card_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            card_type: "data";
            /** Confidence */
            confidence: number;
            payload: components["schemas"]["DataPayload"];
            source: components["schemas"]["KnowledgeSource"];
            /**
             * Status
             * @enum {string}
             */
            status: "active" | "deprecated" | "archived";
            /** Title */
            title: string;
            /** Updated At */
            updated_at: string;
        };
        /** DataKnowledgeCardInput */
        DataKnowledgeCardInput: {
            /** App Id */
            app_id: string;
            /** Card Id */
            card_id?: string | null;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            card_type: "data";
            /** Confidence */
            confidence: number;
            payload: components["schemas"]["DataPayload"];
            source: components["schemas"]["KnowledgeSource"];
            /**
             * Status
             * @default active
             * @enum {string}
             */
            status: "active" | "deprecated" | "archived";
            /** Title */
            title: string;
        };
        /** DataPayload */
        DataPayload: {
            /** Accounts */
            accounts?: string[];
            /** Cleanup Requirements */
            cleanup_requirements?: string[];
            /** Fixtures */
            fixtures?: string[];
            /** Preloaded State */
            preloaded_state?: string[];
        };
        /** DeleteAppData */
        DeleteAppData: {
            /** App Id */
            app_id: string;
        };
        /** DeviceDescriptorData */
        DeviceDescriptorData: {
            /** Availability */
            availability: string;
            /** Device Ref */
            device_ref: string;
            /** Display Name */
            display_name: string;
            /** Is Booted */
            is_booted?: boolean | null;
            /** Kind */
            kind: string;
            /** Platform */
            platform: string;
            /** Raw */
            raw?: {
                [key: string]: unknown;
            };
        };
        /** DeviceInstallData */
        DeviceInstallData: {
            /** Action */
            action: string;
            /** App Id */
            app_id: string;
            /** Artifact Path */
            artifact_path?: string | null;
            /** Device Ref */
            device_ref: string;
            /** Entry Identity */
            entry_identity: string;
            /** Operation Id */
            operation_id: string;
            /** Platform */
            platform: string;
        };
        /** DeviceInstallRequest */
        DeviceInstallRequest: {
            app_target: components["schemas"]["AppTarget"];
            /**
             * Artifact Path
             * Format: path
             */
            artifact_path: string;
            /** Device Ref */
            device_ref: string;
        };
        /** DeviceListData */
        DeviceListData: {
            /** Items */
            items?: components["schemas"]["DeviceDescriptorData"][];
        };
        /** DeviceStateData */
        DeviceStateData: {
            /**
             * Automation Ready
             * @default false
             */
            automation_ready: boolean;
            /** Availability */
            availability: string;
            /** Blockers */
            blockers?: string[];
            /** Device Ref */
            device_ref: string;
            /** Display Name */
            display_name: string;
            /** Is Booted */
            is_booted?: boolean | null;
            /** Is Locked */
            is_locked?: boolean | null;
            /** Is Screen On */
            is_screen_on?: boolean | null;
            /** Kind */
            kind: string;
            /** Platform */
            platform: string;
            /** Raw */
            raw?: {
                [key: string]: unknown;
            };
            /** Unlock Strategies */
            unlock_strategies?: string[];
        };
        /** DeviceUnlockData */
        DeviceUnlockData: {
            after: components["schemas"]["DeviceStateData"];
            before: components["schemas"]["DeviceStateData"];
            /** Changed */
            changed: boolean;
            /** Device Ref */
            device_ref: string;
            /** Message */
            message: string;
            /** Platform */
            platform: string;
            /** Strategy */
            strategy: string;
            /** Success */
            success: boolean;
        };
        /** DomainTermKnowledgeCandidateDraft */
        DomainTermKnowledgeCandidateDraft: {
            /** App Id */
            app_id: string;
            /** Card Id */
            card_id?: string | null;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            card_type: "domain_term";
            /** Confidence */
            confidence: number;
            payload: components["schemas"]["DomainTermPayload"];
            source: components["schemas"]["KnowledgeSource"];
            /** Title */
            title: string;
        };
        /** DomainTermKnowledgeCard */
        DomainTermKnowledgeCard: {
            /** App Id */
            app_id: string;
            /** Card Id */
            card_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            card_type: "domain_term";
            /** Confidence */
            confidence: number;
            payload: components["schemas"]["DomainTermPayload"];
            source: components["schemas"]["KnowledgeSource"];
            /**
             * Status
             * @enum {string}
             */
            status: "active" | "deprecated" | "archived";
            /** Title */
            title: string;
            /** Updated At */
            updated_at: string;
        };
        /** DomainTermKnowledgeCardInput */
        DomainTermKnowledgeCardInput: {
            /** App Id */
            app_id: string;
            /** Card Id */
            card_id?: string | null;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            card_type: "domain_term";
            /** Confidence */
            confidence: number;
            payload: components["schemas"]["DomainTermPayload"];
            source: components["schemas"]["KnowledgeSource"];
            /**
             * Status
             * @default active
             * @enum {string}
             */
            status: "active" | "deprecated" | "archived";
            /** Title */
            title: string;
        };
        /** DomainTermPayload */
        DomainTermPayload: {
            /** Aliases */
            aliases?: string[];
            /** Business Scope */
            business_scope?: string | null;
            /** Meaning */
            meaning: string;
            /** Related Terms */
            related_terms?: string[];
            /** Term */
            term: string;
        };
        /** ErrorResponse */
        ErrorResponse: {
            /** Command */
            command: string;
            error: components["schemas"]["ApiError"];
            /**
             * Ok
             * @default false
             * @constant
             */
            ok: false;
        };
        /** ExecutedPlanResult */
        ExecutedPlanResult: {
            /** Artifact Manifest Version */
            artifact_manifest_version?: number | null;
            /** Contract Versions */
            contract_versions?: {
                [key: string]: string | null;
            };
            /** Diagnostics Path */
            diagnostics_path?: string | null;
            /** Duration Ms */
            duration_ms?: number | null;
            /** Failed Cases */
            failed_cases: number;
            /** Failure Category */
            failure_category?: string | null;
            /**
             * Inconclusive Cases
             * @default 0
             */
            inconclusive_cases: number;
            /** Items */
            items?: components["schemas"]["PlanCaseExecutionItem"][];
            /** Passed Cases */
            passed_cases: number;
            /**
             * Report Path
             * Format: path
             */
            report_path: string;
            /**
             * Stopped Early
             * @default false
             */
            stopped_early: boolean;
            /**
             * Summary Path
             * Format: path
             */
            summary_path: string;
            token_usage?: components["schemas"]["TokenUsage"] | null;
            /** Total Cases */
            total_cases: number;
            /**
             * Upstream Review Enabled
             * @default false
             */
            upstream_review_enabled: boolean;
            /** Upstream Review Orchestration Path */
            upstream_review_orchestration_path?: string | null;
            /** Upstream Review Result Path */
            upstream_review_result_path?: string | null;
            /**
             * Verification Status
             * @enum {string}
             */
            verification_status: "passed" | "failed" | "inconclusive" | "stopped";
            /** Warning Summary */
            warning_summary?: string[];
        };
        /** ExecutionOutcome */
        ExecutionOutcome: {
            /** Error Message */
            error_message?: string | null;
            /** Error Type */
            error_type?: string | null;
            /** Last Action Summary */
            last_action_summary?: string | null;
            /** Last Surface Identity */
            last_surface_identity?: string | null;
            /** Last Target Identity */
            last_target_identity?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "completed" | "failed" | "incomplete";
            /**
             * Steps Completed
             * @default 0
             */
            steps_completed: number;
            /** Stop Reason */
            stop_reason?: string | null;
        };
        /** FinalizeInteractiveSessionRequest */
        FinalizeInteractiveSessionRequest: {
            /**
             * Summary
             * @description Optional agent or host summary recorded on finalize.
             */
            summary?: string | null;
        };
        /** FlowKnowledgeCandidateDraft */
        FlowKnowledgeCandidateDraft: {
            /** App Id */
            app_id: string;
            /** Card Id */
            card_id?: string | null;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            card_type: "flow";
            /** Confidence */
            confidence: number;
            payload: components["schemas"]["FlowPayload"];
            source: components["schemas"]["KnowledgeSource"];
            /** Title */
            title: string;
        };
        /** FlowKnowledgeCard */
        FlowKnowledgeCard: {
            /** App Id */
            app_id: string;
            /** Card Id */
            card_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            card_type: "flow";
            /** Confidence */
            confidence: number;
            payload: components["schemas"]["FlowPayload"];
            source: components["schemas"]["KnowledgeSource"];
            /**
             * Status
             * @enum {string}
             */
            status: "active" | "deprecated" | "archived";
            /** Title */
            title: string;
            /** Updated At */
            updated_at: string;
        };
        /** FlowKnowledgeCardInput */
        FlowKnowledgeCardInput: {
            /** App Id */
            app_id: string;
            /** Card Id */
            card_id?: string | null;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            card_type: "flow";
            /** Confidence */
            confidence: number;
            payload: components["schemas"]["FlowPayload"];
            source: components["schemas"]["KnowledgeSource"];
            /**
             * Status
             * @default active
             * @enum {string}
             */
            status: "active" | "deprecated" | "archived";
            /** Title */
            title: string;
        };
        /** FlowPayload */
        FlowPayload: {
            /** Completion Signals */
            completion_signals?: string[];
            /** Goal */
            goal: string;
            /** Preconditions */
            preconditions?: string[];
            /** Typical Steps */
            typical_steps?: string[];
        };
        /** ForwardingAckRequest */
        ForwardingAckRequest: {
            /** Ack At */
            ack_at?: string;
            device_result?: components["schemas"]["ForwardingDeviceResult"];
            /** Dispatched At */
            dispatched_at?: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "pointer" | "input" | "back";
            /** Payload */
            payload?: components["schemas"]["PointerForwardingPayload"] | components["schemas"]["InputForwardingPayload"] | components["schemas"]["BackForwardingPayload"];
            /** Steps */
            steps?: components["schemas"]["ForwardingStepRequest"][];
        };
        /** ForwardingDeviceResult */
        ForwardingDeviceResult: {
            /** Error Code */
            error_code?: string | null;
            /** Message */
            message?: string | null;
            /**
             * Ok
             * @default true
             */
            ok: boolean;
        };
        /** ForwardingStepRequest */
        ForwardingStepRequest: {
            /** Dispatched At */
            dispatched_at?: string;
            /** Payload */
            payload: components["schemas"]["PointerStepPayload"] | components["schemas"]["TextInjectStepPayload"] | components["schemas"]["KeyPressStepPayload"] | components["schemas"]["KeyTransitionStepPayload"];
            /** Seq */
            seq: number;
            /**
             * Step Kind
             * @enum {string}
             */
            step_kind: "pointer_down" | "pointer_move" | "pointer_up" | "key_press" | "key_down" | "key_up" | "text_inject";
        };
        /** GeminiSectionEditor */
        GeminiSectionEditor: {
            /** Api Key */
            api_key?: string | null;
            /**
             * Api Key Configured
             * @default false
             */
            api_key_configured: boolean;
            /** Base Url */
            base_url?: string | null;
            /**
             * Configured
             * @default false
             */
            configured: boolean;
            /** Credentials Path */
            credentials_path?: string | null;
            /** Location */
            location?: string | null;
            /** Model */
            model?: string | null;
            /** Project */
            project?: string | null;
            /** Timeout Sec */
            timeout_sec?: number | null;
            /**
             * Vertexai
             * @default false
             */
            vertexai: boolean;
        };
        /** GeneratedPlanResult */
        GeneratedPlanResult: {
            /** Case Count */
            case_count: number;
            /** Plan Name */
            plan_name?: string | null;
            /**
             * Plan Path
             * Format: path
             */
            plan_path: string;
            planning_usage?: components["schemas"]["TokenUsage"] | null;
            /**
             * Snapshot Path
             * Format: path
             */
            snapshot_path: string;
        };
        /** GenericOperationEventPayload */
        GenericOperationEventPayload: {
            [key: string]: unknown;
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** HttpBaseConfigEditor */
        HttpBaseConfigEditor: {
            /** Headers */
            headers?: {
                [key: string]: string;
            };
            /** Url */
            url?: string | null;
        };
        /** HttpSetupStep */
        HttpSetupStep: {
            /** Base */
            base: string;
            /** Body */
            body?: unknown | null;
            /** Expected Status */
            expected_status?: number[];
            /** Headers */
            headers?: {
                [key: string]: string;
            };
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "http";
            /**
             * Method
             * @default GET
             * @enum {string}
             */
            method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
            /**
             * Path
             * @default /
             */
            path: string;
            /** Query */
            query?: {
                [key: string]: string;
            };
        };
        /** IOSAppIdentity */
        IOSAppIdentity: {
            /** Bundle Id */
            bundle_id: string;
            /** Wda Bundle Id */
            wda_bundle_id?: string | null;
        };
        /** IOSBridgeConfigEditor */
        IOSBridgeConfigEditor: {
            /**
             * Sudo Enabled
             * @default false
             */
            sudo_enabled: boolean;
            /** Sudo Password */
            sudo_password?: string | null;
            /**
             * Sudo Password Configured
             * @default false
             */
            sudo_password_configured: boolean;
        };
        /** InputForwardingPayload */
        InputForwardingPayload: {
            /**
             * Submit
             * @default false
             */
            submit: boolean;
            /** Text */
            text: string;
        };
        /** InteractiveSessionAbortData */
        InteractiveSessionAbortData: {
            session: components["schemas"]["InteractiveSessionPayload"];
        };
        /** InteractiveSessionCreateData */
        InteractiveSessionCreateData: {
            session: components["schemas"]["InteractiveSessionPayload"];
        };
        /** InteractiveSessionFinalizeData */
        InteractiveSessionFinalizeData: {
            /**
             * Agent Summary
             * @description Optional summary provided at finalize.
             */
            agent_summary?: string | null;
            /**
             * Last Observation Summary
             * @description Summary of the latest observation when available.
             */
            last_observation_summary?: string | null;
            session: components["schemas"]["InteractiveSessionPayload"];
            /**
             * Step Count
             * @description Recorded step count at finalize time.
             */
            step_count: number;
            /**
             * Steps Summary
             * @description Transcript of step summaries.
             */
            steps_summary?: string[];
        };
        /** InteractiveSessionGetData */
        InteractiveSessionGetData: {
            session: components["schemas"]["InteractiveSessionPayload"];
        };
        /** InteractiveSessionPayload */
        InteractiveSessionPayload: {
            /**
             * App Id
             * @description Application identifier associated with the session.
             */
            app_id: string;
            /**
             * Device Ref
             * @description Claimed device reference when available.
             */
            device_ref?: string | null;
            /**
             * Expires At
             * @description Session absolute expiry timestamp in ISO format.
             */
            expires_at: string;
            /**
             * Finalized Agent Summary
             * @description Agent summary from finalize when available.
             */
            finalized_agent_summary?: string | null;
            /**
             * Idle Expires At
             * @description Session idle expiry timestamp in ISO format.
             */
            idle_expires_at: string;
            /**
             * Last Active At
             * @description Last agent activity timestamp in ISO format.
             */
            last_active_at: string;
            /**
             * Last Observation Summary
             * @description Summary of the latest observation when available.
             */
            last_observation_summary?: string | null;
            /**
             * Platform
             * @description Interactive target platform.
             */
            platform: string;
            /**
             * Session Id
             * @description Interactive session identifier.
             */
            session_id: string;
            /**
             * Started At
             * @description Session start timestamp in ISO format.
             */
            started_at: string;
            /**
             * Status
             * @description Current interactive session status.
             * @enum {string}
             */
            status: "created" | "waiting_agent" | "acting" | "finalized" | "aborted" | "expired";
            /**
             * Step Count
             * @description Current recorded step count.
             */
            step_count: number;
            /**
             * Updated At
             * @description Session update timestamp in ISO format.
             */
            updated_at: string;
        };
        /** InteractiveSessionStateData */
        InteractiveSessionStateData: {
            /** Expires At */
            expires_at?: string | null;
            /** Idle Expires At */
            idle_expires_at?: string | null;
            /** Last Active At */
            last_active_at?: string | null;
            /** Session Id */
            session_id: string;
            /** Status */
            status: string;
        };
        /** IssueKnowledgeCandidateDraft */
        IssueKnowledgeCandidateDraft: {
            /** App Id */
            app_id: string;
            /** Card Id */
            card_id?: string | null;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            card_type: "issue";
            /** Confidence */
            confidence: number;
            payload: components["schemas"]["IssuePayload"];
            source: components["schemas"]["KnowledgeSource"];
            /** Title */
            title: string;
        };
        /** IssueKnowledgeCard */
        IssueKnowledgeCard: {
            /** App Id */
            app_id: string;
            /** Card Id */
            card_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            card_type: "issue";
            /** Confidence */
            confidence: number;
            payload: components["schemas"]["IssuePayload"];
            source: components["schemas"]["KnowledgeSource"];
            /**
             * Status
             * @enum {string}
             */
            status: "active" | "deprecated" | "archived";
            /** Title */
            title: string;
            /** Updated At */
            updated_at: string;
        };
        /** IssueKnowledgeCardInput */
        IssueKnowledgeCardInput: {
            /** App Id */
            app_id: string;
            /** Card Id */
            card_id?: string | null;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            card_type: "issue";
            /** Confidence */
            confidence: number;
            payload: components["schemas"]["IssuePayload"];
            source: components["schemas"]["KnowledgeSource"];
            /**
             * Status
             * @default active
             * @enum {string}
             */
            status: "active" | "deprecated" | "archived";
            /** Title */
            title: string;
        };
        /** IssuePayload */
        IssuePayload: {
            /** Severity */
            severity?: string | null;
            /** Symptoms */
            symptoms?: string[];
            /** Trigger Conditions */
            trigger_conditions?: string[];
            /** Workaround */
            workaround?: string | null;
        };
        /** JudgeCompactUiNode */
        JudgeCompactUiNode: {
            /** Bounds */
            bounds?: number[];
            /** Class Name */
            class_name?: string | null;
            /** Content Desc */
            content_desc?: string | null;
            /** Node Id */
            node_id?: string | null;
            /** Parent Node Id */
            parent_node_id?: string | null;
            /** Resource Id */
            resource_id?: string | null;
            /** Role */
            role?: string | null;
            /** Stable Key */
            stable_key?: string | null;
            state?: components["schemas"]["JudgeCompactUiNodeState"];
            /** Text */
            text?: string | null;
            /** Visual Ids */
            visual_ids?: string[];
        };
        /** JudgeCompactUiNodeState */
        JudgeCompactUiNodeState: {
            /** Checkable */
            checkable?: boolean | null;
            /** Checked */
            checked?: boolean | null;
            /** Clickable */
            clickable?: boolean | null;
            /** Enabled */
            enabled?: boolean | null;
            /** Focused */
            focused?: boolean | null;
            /** Scrollable */
            scrollable?: boolean | null;
            /** Selected */
            selected?: boolean | null;
        };
        /** JudgeCompactUiTree */
        JudgeCompactUiTree: {
            /** Focus Term Count */
            focus_term_count?: number | null;
            /**
             * Node Count
             * @default 0
             */
            node_count: number;
            /** Nodes */
            nodes?: components["schemas"]["JudgeCompactUiNode"][];
        };
        /** JudgeDecisionEventPayload */
        JudgeDecisionEventPayload: {
            /** Decision Type */
            decision_type?: string | null;
            /** Reason */
            reason?: string | null;
            /** Verdict */
            verdict?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** JudgeDecisionTraceEvidence */
        JudgeDecisionTraceEvidence: {
            /** Evidence Id */
            evidence_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "decision_trace";
            payload: components["schemas"]["JudgeDecisionTraceEvidencePayload"];
            /**
             * Source
             * @default artifact
             * @constant
             */
            source: "artifact";
            /** Summary */
            summary: string;
        };
        /** JudgeDecisionTraceEvidencePayload */
        JudgeDecisionTraceEvidencePayload: {
            /** Action */
            action?: string | null;
            /** Arguments */
            arguments?: {
                [key: string]: unknown;
            };
            /** Attempt Index */
            attempt_index?: number | null;
            /** Decision */
            decision?: string | null;
            /** Path */
            path?: string | null;
            /** Raw Line */
            raw_line?: string | null;
            /** Result Summary */
            result_summary?: string | null;
            /** Seeded Element Count */
            seeded_element_count?: number | null;
            /** Step Index */
            step_index?: number | null;
            /** Summary */
            summary?: string | null;
            /** Tool Name */
            tool_name?: string | null;
            /** Tool Names */
            tool_names?: string[];
            /** Ui Elements Summary */
            ui_elements_summary?: string | null;
            /** Will Retry */
            will_retry?: boolean | null;
        };
        /** JudgeEventEvidence */
        JudgeEventEvidence: {
            /** Evidence Id */
            evidence_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "event";
            payload: components["schemas"]["JudgeEventEvidencePayload"];
            /**
             * Source
             * @default event
             * @constant
             */
            source: "event";
            /** Summary */
            summary: string;
        };
        /** JudgeEventEvidencePayload */
        JudgeEventEvidencePayload: {
            /** Data */
            data?: {
                [key: string]: unknown;
            };
            /** Event Type */
            event_type: string;
            /** Message */
            message?: string | null;
            /** Timestamp */
            timestamp: string;
        };
        /** JudgeExecutionEvidence */
        JudgeExecutionEvidence: {
            /** Evidence Id */
            evidence_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "execution_outcome";
            payload: components["schemas"]["JudgeExecutionEvidencePayload"];
            /**
             * Source
             * @default execution
             * @constant
             */
            source: "execution";
            /** Summary */
            summary: string;
        };
        /** JudgeExecutionEvidencePayload */
        JudgeExecutionEvidencePayload: {
            /** Error Message */
            error_message?: string | null;
            /** Error Type */
            error_type?: string | null;
            /** Last Action Summary */
            last_action_summary?: string | null;
            /** Last Surface Identity */
            last_surface_identity?: string | null;
            /** Last Target Identity */
            last_target_identity?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "completed" | "failed" | "incomplete";
            /**
             * Steps Completed
             * @default 0
             */
            steps_completed: number;
            /** Stop Reason */
            stop_reason?: string | null;
        };
        /** JudgeFocusHit */
        JudgeFocusHit: {
            /** Label */
            label?: string | null;
            /** Node Id */
            node_id?: string | null;
            /** Score */
            score?: number | null;
        };
        /** JudgeRunnerHistoryEntry */
        JudgeRunnerHistoryEntry: {
            /** Action Type */
            action_type?: string | null;
            /** Outcome Summary */
            outcome_summary?: string | null;
            /** Record */
            record?: {
                [key: string]: unknown;
            } | null;
            /** Step Index */
            step_index?: number | null;
            /** Summary */
            summary?: string | null;
        };
        /** JudgeRunnerHistoryEvidence */
        JudgeRunnerHistoryEvidence: {
            /** Evidence Id */
            evidence_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "runner_history";
            payload: components["schemas"]["JudgeRunnerHistoryEvidencePayload"];
            /**
             * Source
             * @default artifact
             * @constant
             */
            source: "artifact";
            /** Summary */
            summary: string;
        };
        /** JudgeRunnerHistoryEvidencePayload */
        JudgeRunnerHistoryEvidencePayload: {
            /** Entries */
            entries?: components["schemas"]["JudgeRunnerHistoryEntry"][];
            /** Excerpt */
            excerpt?: components["schemas"]["JudgeRunnerHistoryEntry"][];
            /** Latest Step Index */
            latest_step_index?: number | null;
            /** Path */
            path?: string | null;
        };
        /** JudgeRunnerIssueEvidence */
        JudgeRunnerIssueEvidence: {
            /** Evidence Id */
            evidence_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "runner_issue";
            payload: components["schemas"]["JudgeRunnerIssueEvidencePayload"];
            /**
             * Source
             * @default artifact
             * @constant
             */
            source: "artifact";
            /** Summary */
            summary: string;
        };
        /** JudgeRunnerIssueEvidencePayload */
        JudgeRunnerIssueEvidencePayload: {
            issue: components["schemas"]["JudgeRunnerIssueRecord"];
            /** Path */
            path?: string | null;
        };
        /** JudgeRunnerIssueRecord */
        JudgeRunnerIssueRecord: {
            /** Record */
            record?: {
                [key: string]: unknown;
            } | null;
            /** Severity */
            severity?: string | null;
            /** Step Index */
            step_index?: number | null;
            /** Summary */
            summary?: string | null;
        };
        /** JudgeRunnerMemoryEntry */
        JudgeRunnerMemoryEntry: {
            /** Key */
            key?: string | null;
            /** Summary */
            summary?: string | null;
            /** Timestamp */
            timestamp?: string | null;
            /** Updated Step Index */
            updated_step_index?: number | null;
            /** Value */
            value?: unknown;
        };
        /** JudgeRunnerMemoryEvidence */
        JudgeRunnerMemoryEvidence: {
            /** Evidence Id */
            evidence_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "runner_memory";
            payload: components["schemas"]["JudgeRunnerMemoryEvidencePayload"];
            /**
             * Source
             * @default artifact
             * @constant
             */
            source: "artifact";
            /** Summary */
            summary: string;
        };
        /** JudgeRunnerMemoryEvidencePayload */
        JudgeRunnerMemoryEvidencePayload: {
            /** Entries */
            entries?: components["schemas"]["JudgeRunnerMemoryEntry"][];
            /** Excerpt */
            excerpt?: components["schemas"]["JudgeRunnerMemoryEntry"][];
            /** Path */
            path?: string | null;
        };
        /** JudgeRuntimeErrorLogEvidence */
        JudgeRuntimeErrorLogEvidence: {
            /** Evidence Id */
            evidence_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "runtime_error_log";
            payload: components["schemas"]["JudgeRuntimeErrorLogEvidencePayload"];
            /**
             * Source
             * @default artifact
             * @constant
             */
            source: "artifact";
            /** Summary */
            summary: string;
        };
        /** JudgeRuntimeErrorLogEvidencePayload */
        JudgeRuntimeErrorLogEvidencePayload: {
            /** Entries */
            entries?: components["schemas"]["JudgeRuntimeLogEntry"][];
            /** Excerpt */
            excerpt: string;
            /** Path */
            path?: string | null;
            /** Step Indexes */
            step_indexes?: number[];
        };
        /** JudgeRuntimeEventPayload */
        JudgeRuntimeEventPayload: {
            /** Agent Role */
            agent_role: string;
            /** Error Type */
            error_type?: string | null;
            /** Event Timestamp */
            event_timestamp?: string | null;
            /** Evidence Count */
            evidence_count?: number | null;
            /** Lifecycle State */
            lifecycle_state: string;
            /** Primary Evidence Count */
            primary_evidence_count?: number | null;
            /** Prompt Path */
            prompt_path?: string | null;
            /** Root Dir */
            root_dir?: string | null;
            /** Runner Event Type */
            runner_event_type?: string | null;
            /** Supporting Evidence Count */
            supporting_evidence_count?: number | null;
            /** Timestamp */
            timestamp?: string | null;
            /** Tool Call Count */
            tool_call_count?: number | null;
            /** Verdict */
            verdict?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** JudgeRuntimeLogEntry */
        JudgeRuntimeLogEntry: {
            /** Message */
            message: string;
            /** Source */
            source?: string | null;
            /** Step Index */
            step_index?: number | null;
            /** Surface Identity */
            surface_identity?: string | null;
        };
        /** JudgeScreenDiffEvidence */
        JudgeScreenDiffEvidence: {
            /** Evidence Id */
            evidence_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "screen_diff";
            payload: components["schemas"]["JudgeScreenDiffEvidencePayload"];
            /**
             * Source
             * @default artifact
             * @constant
             */
            source: "artifact";
            /** Summary */
            summary: string;
        };
        /** JudgeScreenDiffEvidencePayload */
        JudgeScreenDiffEvidencePayload: {
            /** Appeared Labels */
            appeared_labels?: string[];
            /** Appeared Nodes */
            appeared_nodes?: components["schemas"]["JudgeScreenNodeChange"][];
            /** Disappeared Labels */
            disappeared_labels?: string[];
            /** Disappeared Nodes */
            disappeared_nodes?: components["schemas"]["JudgeScreenNodeChange"][];
            /** Linked Visual Changes */
            linked_visual_changes?: string[];
            /** Path */
            path: string;
            /** Step Index */
            step_index: number;
            /** Summary */
            summary?: string | null;
            /** Updated Labels */
            updated_labels?: string[];
            /** Updated Nodes */
            updated_nodes?: components["schemas"]["JudgeScreenNodeChange"][];
        };
        /** JudgeScreenFrameEvidence */
        JudgeScreenFrameEvidence: {
            /** Evidence Id */
            evidence_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "screen_frame";
            payload: components["schemas"]["JudgeScreenFrameEvidencePayload"];
            /**
             * Source
             * @default artifact
             * @constant
             */
            source: "artifact";
            /** Summary */
            summary: string;
        };
        /** JudgeScreenFrameEvidencePayload */
        JudgeScreenFrameEvidencePayload: {
            compact_tree?: components["schemas"]["JudgeCompactUiTree"];
            /** Focus Hits */
            focus_hits?: components["schemas"]["JudgeFocusHit"][];
            /** Package */
            package?: string | null;
            /** Path */
            path: string;
            /** Step Index */
            step_index: number;
            /** Tree Available */
            tree_available?: boolean | null;
            /** Tree Summary */
            tree_summary?: string | null;
        };
        /** JudgeScreenNodeChange */
        JudgeScreenNodeChange: {
            /** Change Type */
            change_type?: string | null;
            /** Label */
            label?: string | null;
            /** Stable Key */
            stable_key?: string | null;
        };
        /** JudgeScreenshotEvidence */
        JudgeScreenshotEvidence: {
            /** Evidence Id */
            evidence_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "screenshot";
            payload: components["schemas"]["JudgeScreenshotEvidencePayload"];
            /**
             * Source
             * @default artifact
             * @constant
             */
            source: "artifact";
            /** Summary */
            summary: string;
        };
        /** JudgeScreenshotEvidencePayload */
        JudgeScreenshotEvidencePayload: {
            /** Action Summary */
            action_summary?: string | null;
            /** Diff Evidence Id */
            diff_evidence_id?: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "raw" | "annotated";
            /** Observation Summary */
            observation_summary?: string | null;
            /** Package */
            package?: string | null;
            /** Path */
            path: string;
            /** Screenshot Id */
            screenshot_id: string;
            /** Step Index */
            step_index: number;
            /** Tree Evidence Id */
            tree_evidence_id?: string | null;
        };
        /** KeyPressStepPayload */
        KeyPressStepPayload: {
            /** Key */
            key: string;
        };
        /** KeyTransitionStepPayload */
        KeyTransitionStepPayload: {
            /** Key */
            key: string;
        };
        /** KnowledgeCandidateApproveData */
        KnowledgeCandidateApproveData: {
            /** Build Manifest Path */
            build_manifest_path: string;
            /**
             * Cache Hit
             * @default false
             */
            cache_hit: boolean;
            candidate: components["schemas"]["KnowledgeCandidateRecord"];
            /** Db Path */
            db_path: string;
            /** Rebuilt Cards */
            rebuilt_cards: number;
            /** Resolved Card Id */
            resolved_card_id: string;
            /** Skipped Cards */
            skipped_cards: number;
        };
        /** KnowledgeCandidateDecisionRequest */
        KnowledgeCandidateDecisionRequest: {
            /** Review Note */
            review_note?: string | null;
            /** Reviewed By */
            reviewed_by?: string | null;
        };
        /** KnowledgeCandidateListData */
        KnowledgeCandidateListData: {
            /** Items */
            items?: components["schemas"]["KnowledgeCandidateRecord"][];
            /**
             * Total Count
             * @default 0
             */
            total_count: number;
        };
        /** KnowledgeCandidateRecord */
        KnowledgeCandidateRecord: {
            /** App Id */
            app_id: string;
            /** Candidate */
            candidate: components["schemas"]["ScreenKnowledgeCandidateDraft"] | components["schemas"]["FlowKnowledgeCandidateDraft"] | components["schemas"]["AssertionKnowledgeCandidateDraft"] | components["schemas"]["IssueKnowledgeCandidateDraft"] | components["schemas"]["DataKnowledgeCandidateDraft"] | components["schemas"]["PolicyKnowledgeCandidateDraft"] | components["schemas"]["DomainTermKnowledgeCandidateDraft"];
            /** Candidate Id */
            candidate_id: string;
            /** Evidence Refs */
            evidence_refs?: string[];
            /** Resolved Card Id */
            resolved_card_id?: string | null;
            /** Review Note */
            review_note?: string | null;
            /** Reviewed At */
            reviewed_at?: string | null;
            /** Reviewed By */
            reviewed_by?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "pending_review" | "approved" | "rejected";
            /** Submitted At */
            submitted_at: string;
        };
        /** KnowledgeCandidateRejectData */
        KnowledgeCandidateRejectData: {
            candidate: components["schemas"]["KnowledgeCandidateRecord"];
        };
        /** KnowledgeCardDeleteData */
        KnowledgeCardDeleteData: {
            /** Build Manifest Path */
            build_manifest_path: string;
            /**
             * Cache Hit
             * @default false
             */
            cache_hit: boolean;
            /** Db Path */
            db_path: string;
            /** Deleted Card Id */
            deleted_card_id: string;
            /** Rebuilt Cards */
            rebuilt_cards: number;
            /** Skipped Cards */
            skipped_cards: number;
            /** Total Cards */
            total_cards: number;
        };
        /** KnowledgeCardGetData */
        KnowledgeCardGetData: {
            /** Card */
            card: components["schemas"]["ScreenKnowledgeCard"] | components["schemas"]["FlowKnowledgeCard"] | components["schemas"]["AssertionKnowledgeCard"] | components["schemas"]["IssueKnowledgeCard"] | components["schemas"]["DataKnowledgeCard"] | components["schemas"]["PolicyKnowledgeCard"] | components["schemas"]["DomainTermKnowledgeCard"];
        };
        /** KnowledgeCardListData */
        KnowledgeCardListData: {
            /** Items */
            items?: (components["schemas"]["ScreenKnowledgeCard"] | components["schemas"]["FlowKnowledgeCard"] | components["schemas"]["AssertionKnowledgeCard"] | components["schemas"]["IssueKnowledgeCard"] | components["schemas"]["DataKnowledgeCard"] | components["schemas"]["PolicyKnowledgeCard"] | components["schemas"]["DomainTermKnowledgeCard"])[];
            /**
             * Limit
             * @default 0
             */
            limit: number;
            /**
             * Offset
             * @default 0
             */
            offset: number;
            /**
             * Total Count
             * @default 0
             */
            total_count: number;
        };
        /** KnowledgeCardMutationData */
        KnowledgeCardMutationData: {
            /** Build Manifest Path */
            build_manifest_path: string;
            /**
             * Cache Hit
             * @default false
             */
            cache_hit: boolean;
            /** Card */
            card: components["schemas"]["ScreenKnowledgeCard"] | components["schemas"]["FlowKnowledgeCard"] | components["schemas"]["AssertionKnowledgeCard"] | components["schemas"]["IssueKnowledgeCard"] | components["schemas"]["DataKnowledgeCard"] | components["schemas"]["PolicyKnowledgeCard"] | components["schemas"]["DomainTermKnowledgeCard"];
            /** Db Path */
            db_path: string;
            /** Rebuilt Cards */
            rebuilt_cards: number;
            /** Skipped Cards */
            skipped_cards: number;
            /** Total Cards */
            total_cards: number;
        };
        /** KnowledgeCardWriteRequest */
        KnowledgeCardWriteRequest: {
            /** Card */
            card: components["schemas"]["ScreenKnowledgeCardInput"] | components["schemas"]["FlowKnowledgeCardInput"] | components["schemas"]["AssertionKnowledgeCardInput"] | components["schemas"]["IssueKnowledgeCardInput"] | components["schemas"]["DataKnowledgeCardInput"] | components["schemas"]["PolicyKnowledgeCardInput"] | components["schemas"]["DomainTermKnowledgeCardInput"];
        };
        /** KnowledgePostActionOperationResultPayload */
        KnowledgePostActionOperationResultPayload: {
            /** Artifacts */
            artifacts: {
                [key: string]: string;
            };
            /** Candidate Id */
            candidate_id?: string | null;
            /** Knowledge Post Action Diagnostics Path */
            knowledge_post_action_diagnostics_path: string;
            /** Knowledge Post Action Request Path */
            knowledge_post_action_request_path: string;
            /** Knowledge Post Action Result Path */
            knowledge_post_action_result_path: string;
            /** Knowledge Post Action Tool Calls Path */
            knowledge_post_action_tool_calls_path: string;
            /** Skip Reason */
            skip_reason?: string | null;
            /**
             * Submitted
             * @default false
             */
            submitted: boolean;
            /** Summary */
            summary: string;
        };
        /** KnowledgeSource */
        KnowledgeSource: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "import" | "review" | "knowledge_agent" | "manual";
            /** Note */
            note?: string | null;
            /** Ref */
            ref?: string | null;
        };
        /** KnowledgeTimelineEventPayload */
        KnowledgeTimelineEventPayload: {
            /** Agent Input Path */
            agent_input_path?: string | null;
            /** Agent Role */
            agent_role?: string | null;
            /** Artifact Count */
            artifact_count?: number | null;
            /** Candidate Count */
            candidate_count?: number | null;
            /** Candidate Id */
            candidate_id?: string | null;
            /** Candidate Title */
            candidate_title?: string | null;
            /** Card Type */
            card_type?: string | null;
            /** Event Timestamp */
            event_timestamp?: string | null;
            /** Generated Candidate Count */
            generated_candidate_count?: number | null;
            /** Judge Verdict */
            judge_verdict?: string | null;
            /** Lifecycle State */
            lifecycle_state?: string | null;
            /** Prompt Path */
            prompt_path?: string | null;
            /** Skip Reason */
            skip_reason?: string | null;
            /** Submitted */
            submitted?: boolean | null;
            /** Timestamp */
            timestamp?: string | null;
            /** Tool Call Count */
            tool_call_count?: number | null;
            /** Tool Calls */
            tool_calls?: string[] | null;
            /** Tool Index */
            tool_index?: number | null;
            /** Tool Name */
            tool_name?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** LatestOptimizeOperationData */
        LatestOptimizeOperationData: {
            /** Created At */
            created_at: string;
            /** Error Message */
            error_message?: string | null;
            /** Finished At */
            finished_at?: string | null;
            /** Operation Id */
            operation_id: string;
            /** Patched Fields */
            patched_fields?: string[];
            /** Started At */
            started_at?: string | null;
            /** Status */
            status: string;
            /** Summary */
            summary?: string | null;
        };
        /** LlmRequestTimelinePayload */
        LlmRequestTimelinePayload: {
            /** Llm Model */
            llm_model?: string | null;
            /** Llm Provider */
            llm_provider?: string | null;
            /** Llm Request Id */
            llm_request_id?: string | null;
            /** Llm Text */
            llm_text?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** LlmResponseTimelinePayload */
        LlmResponseTimelinePayload: {
            /** Llm Model */
            llm_model?: string | null;
            /** Llm Provider */
            llm_provider?: string | null;
            /** Llm Request Id */
            llm_request_id?: string | null;
            /** Llm Status Code */
            llm_status_code?: number | null;
            /** Llm Text */
            llm_text?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** LogEventPayload */
        LogEventPayload: {
            /** Level */
            level: string;
            /** Logger */
            logger: string;
        } & {
            [key: string]: unknown;
        };
        /** ObservationSnapshot */
        ObservationSnapshot: {
            /** Captured At */
            captured_at?: string;
            current_app_state?: components["schemas"]["RecordedCurrentAppState"] | null;
            /** Entry Identity */
            entry_identity?: string | null;
            /** Frame Seq */
            frame_seq?: number | null;
            /**
             * Image Path
             * Format: path
             */
            image_path: string;
            /**
             * Metadata Path
             * Format: path
             */
            metadata_path: string;
            /** Observation Id */
            observation_id: string;
            /** Recording Id */
            recording_id: string;
            /** Screenshot Hash */
            screenshot_hash?: string | null;
            /**
             * Stabilized
             * @default true
             */
            stabilized: boolean;
            /** Surface Identity */
            surface_identity?: string | null;
            /**
             * Tree Available
             * @default false
             */
            tree_available: boolean;
            /** Ui Tree Hash */
            ui_tree_hash?: string | null;
            /** Ui Tree Path */
            ui_tree_path?: string | null;
        };
        /** ObserveTapRequest */
        ObserveTapRequest: {
            /** Height */
            height: number;
            /**
             * Source
             * @default scrcpy_bridge
             */
            source: string;
            /** Width */
            width: number;
            /** X */
            x: number;
            /** X Ratio */
            x_ratio?: number | null;
            /** Y */
            y: number;
            /** Y Ratio */
            y_ratio?: number | null;
        };
        /** OpenAICompatibleSectionEditor */
        OpenAICompatibleSectionEditor: {
            /** Api Key */
            api_key?: string | null;
            /**
             * Api Key Configured
             * @default false
             */
            api_key_configured: boolean;
            /** Base Url */
            base_url?: string | null;
            /**
             * Configured
             * @default false
             */
            configured: boolean;
            /** Extra Headers */
            extra_headers?: {
                [key: string]: string;
            };
            /** Model */
            model?: string | null;
            /**
             * Output Strategy
             * @default auto
             * @enum {string}
             */
            output_strategy: "auto" | "prompted";
            /** Thinking */
            thinking?: boolean | null;
            /** Timeout Sec */
            timeout_sec?: number | null;
        };
        /** OperationArtifactsData */
        OperationArtifactsData: {
            /** Artifact Groups */
            artifact_groups?: components["schemas"]["RunArtifactGroupData"][];
            /** Artifact Manifest Path */
            artifact_manifest_path?: string | null;
            /** Artifact Manifest Version */
            artifact_manifest_version?: number | null;
            /** Attempt Usages */
            attempt_usages?: components["schemas"]["AttemptTokenUsageData"][];
            /** Case Runs */
            case_runs?: components["schemas"]["CaseRunArtifactSummaryData"][];
            /** Conflict Reason */
            conflict_reason?: string | null;
            /** Device Ref */
            device_ref?: string | null;
            /** Diagnostics Path */
            diagnostics_path?: string | null;
            /** Duration Ms */
            duration_ms?: number | null;
            execution_usage?: components["schemas"]["TokenUsageData"] | null;
            /** Failure Category */
            failure_category?: string | null;
            /** Operation Id */
            operation_id: string;
            /** Phase */
            phase?: string | null;
            planning_usage?: components["schemas"]["TokenUsageData"] | null;
            /** Platform */
            platform?: string | null;
            /** Primary Artifact Ids */
            primary_artifact_ids?: string[];
            /** Primary Artifacts */
            primary_artifacts?: components["schemas"]["RunArtifactItemData"][];
            /** Repro Dir */
            repro_dir?: string | null;
            /** Reproduction Entries */
            reproduction_entries?: components["schemas"]["ReproductionEntry"][];
            /** Resource Scope */
            resource_scope?: string | null;
            /** Run Type */
            run_type?: string | null;
            schema_versions?: components["schemas"]["ArtifactSchemaVersions"];
            /** Source Recording Id */
            source_recording_id?: string | null;
            /** Status */
            status: string;
            /** Target Label */
            target_label?: string | null;
            /** Title */
            title?: string | null;
            token_usage?: components["schemas"]["TokenUsageData"] | null;
            upstream_review?: components["schemas"]["UpstreamReviewArtifacts"] | null;
            /** Verification Verdict */
            verification_verdict?: string | null;
            /** Warning Summary */
            warning_summary?: string[];
        };
        /** OperationChildItemData */
        OperationChildItemData: {
            /** Case Id */
            case_id?: string | null;
            /** Created At */
            created_at: string;
            /** Error Code */
            error_code?: string | null;
            /** Error Message */
            error_message?: string | null;
            /** Finished At */
            finished_at?: string | null;
            /** Kind */
            kind?: string | null;
            /** Operation Id */
            operation_id: string;
            /** Plan Id */
            plan_id?: string | null;
            /** Position Index */
            position_index?: number | null;
            /** Position Label */
            position_label?: string | null;
            /** Run Type */
            run_type?: string | null;
            /** Started At */
            started_at?: string | null;
            /** Status */
            status: string;
            /** Title */
            title?: string | null;
            token_usage?: components["schemas"]["TokenUsageData"] | null;
            /** Verification Verdict */
            verification_verdict?: string | null;
        };
        /** OperationChildrenData */
        OperationChildrenData: {
            /** Items */
            items?: components["schemas"]["OperationChildItemData"][];
            /** Operation Id */
            operation_id: string;
        };
        /** OperationDetailData */
        OperationDetailData: {
            aggregate?: components["schemas"]["BatchRunAggregateData"] | null;
            /** App Id */
            app_id?: string | null;
            /** Artifact Manifest Path */
            artifact_manifest_path?: string | null;
            /** Artifact Manifest Version */
            artifact_manifest_version?: number | null;
            /** Attempt Usages */
            attempt_usages?: components["schemas"]["AttemptTokenUsageData"][];
            /** Batch Id */
            batch_id?: string | null;
            /** Batch Kind */
            batch_kind?: string | null;
            /**
             * Cancel Requested
             * @default false
             */
            cancel_requested: boolean;
            /** Case Id */
            case_id?: string | null;
            /** Children Preview */
            children_preview?: components["schemas"]["OperationChildItemData"][];
            /** Conflict Reason */
            conflict_reason?: string | null;
            /** Created At */
            created_at: string;
            /** Current Child Case Id */
            current_child_case_id?: string | null;
            /** Current Child Operation Id */
            current_child_operation_id?: string | null;
            /** Device Ref */
            device_ref?: string | null;
            /** Diagnostics Path */
            diagnostics_path?: string | null;
            /** Duration Ms */
            duration_ms?: number | null;
            /** Error Code */
            error_code?: string | null;
            /** Error Message */
            error_message?: string | null;
            execution_usage?: components["schemas"]["TokenUsageData"] | null;
            /** Failure Category */
            failure_category?: string | null;
            /** Finished At */
            finished_at?: string | null;
            /**
             * Is Batch
             * @default false
             */
            is_batch: boolean;
            /** Kind */
            kind: string;
            /** Operation Id */
            operation_id: string;
            /** Parent Operation Id */
            parent_operation_id?: string | null;
            /** Phase */
            phase?: string | null;
            /** Pid */
            pid?: number | null;
            /** Plan Id */
            plan_id?: string | null;
            planning_usage?: components["schemas"]["TokenUsageData"] | null;
            /** Platform */
            platform?: string | null;
            /** Position Index */
            position_index?: number | null;
            /** Position Label */
            position_label?: string | null;
            /** Primary Artifact Ids */
            primary_artifact_ids?: string[];
            progress?: components["schemas"]["OperationProgressData"] | null;
            /** Repro Dir */
            repro_dir?: string | null;
            /** Resource Scope */
            resource_scope?: string | null;
            /** Result */
            result?: components["schemas"]["RunCaseResultData"] | components["schemas"]["PhasedOperationResult"] | components["schemas"]["RunPlanOperationResultPayload"] | components["schemas"]["RunPlansResultPayload"] | components["schemas"]["VerifyChangeOperationResultPayload"] | components["schemas"]["ReviewOperationResultPayload"] | components["schemas"]["OptimizeCaseOperationResultPayload"] | components["schemas"]["KnowledgePostActionOperationResultPayload"] | components["schemas"]["RecordingSessionTerminalResult"] | components["schemas"]["RecordingReplayOperationResult"] | components["schemas"]["RecordingAnalysisResult"] | null;
            /** Run Type */
            run_type?: string | null;
            schema_versions?: components["schemas"]["ArtifactSchemaVersions"];
            /** Source Recording Id */
            source_recording_id?: string | null;
            /** Started At */
            started_at?: string | null;
            /** Status */
            status: string;
            /** Target Label */
            target_label?: string | null;
            /** Title */
            title?: string | null;
            token_usage?: components["schemas"]["TokenUsageData"] | null;
            /** Verification Verdict */
            verification_verdict?: string | null;
            /** Warning Summary */
            warning_summary?: string[];
        };
        /** OperationEventItemData */
        OperationEventItemData: {
            /** Agent Role */
            agent_role?: string | null;
            /** App Id */
            app_id?: string | null;
            /** Attempt Index */
            attempt_index?: number | null;
            /** Case Id */
            case_id?: string | null;
            /** Child Operation Id */
            child_operation_id?: string | null;
            /** Data Json */
            data_json?: components["schemas"]["RunStartedEventPayload"] | components["schemas"]["StepStartedEventPayload"] | components["schemas"]["PerceptionCompletedEventPayload"] | components["schemas"]["RunnerToolCalledEventPayload"] | components["schemas"]["RunnerContractMissEventPayload"] | components["schemas"]["RunnerDecisionCompletedEventPayload"] | components["schemas"]["RunnerActionEventPayload"] | components["schemas"]["RunStoppedEventPayload"] | components["schemas"]["RunFailedEventPayload"] | components["schemas"]["LogEventPayload"] | components["schemas"]["LlmRequestTimelinePayload"] | components["schemas"]["LlmResponseTimelinePayload"] | components["schemas"]["WorkflowStartedEventPayload"] | components["schemas"]["WorkflowAttemptStartedEventPayload"] | components["schemas"]["WorkflowAttemptFinishedEventPayload"] | components["schemas"]["WorkflowRetryScheduledEventPayload"] | components["schemas"]["WorkflowFinishedEventPayload"] | components["schemas"]["JudgeDecisionEventPayload"] | components["schemas"]["AgentRuntimeLifecycleEventPayload"] | components["schemas"]["ContextPrepareParamsResolvedEventPayload"] | components["schemas"]["ContextPrepareDeviceReadyEventPayload"] | components["schemas"]["ContextPreparePerceptionReadyEventPayload"] | components["schemas"]["ContextPrepareSetupStartedEventPayload"] | components["schemas"]["ContextPrepareSetupStepEventPayload"] | components["schemas"]["ContextPrepareSetupReadyEventPayload"] | components["schemas"]["ContextPrepareStartStateStartedEventPayload"] | components["schemas"]["ContextPrepareStartStateStepEventPayload"] | components["schemas"]["ContextPrepareStartStateReadyEventPayload"] | components["schemas"]["ContextPrepareFailedEventPayload"] | components["schemas"]["RunnerRuntimeEventPayload"] | components["schemas"]["JudgeRuntimeEventPayload"] | components["schemas"]["PostRunChildOperationEventPayload"] | components["schemas"]["OperationSubmittedEventPayload"] | components["schemas"]["OperationStartedEventPayload"] | components["schemas"]["OperationInterruptedEventPayload"] | components["schemas"]["ResourceClaimedEventPayload"] | components["schemas"]["ResourceReleasedEventPayload"] | components["schemas"]["ResourceConflictEventPayload"] | components["schemas"]["BatchStartedEventPayload"] | components["schemas"]["BatchChildStartedEventPayload"] | components["schemas"]["BatchChildFinishedEventPayload"] | components["schemas"]["BatchStoppedEarlyEventPayload"] | components["schemas"]["BatchFinishedEventPayload"] | components["schemas"]["PlanningTimelineEventPayload"] | components["schemas"]["ChangeVerificationReviewContractLoadedPayload"] | components["schemas"]["ChangeVerificationCasesReadyPayload"] | components["schemas"]["ChangeVerificationPlanSavedPayload"] | components["schemas"]["ReviewTimelineEventPayload"] | components["schemas"]["KnowledgeTimelineEventPayload"] | components["schemas"]["OptimizeTimelineEventPayload"] | components["schemas"]["RecordingIdEventPayload"] | components["schemas"]["RecordingStartedEventPayload"] | components["schemas"]["RecordingTapObservedEventPayload"] | components["schemas"]["RecordingInteractionRecordedEventPayload"] | components["schemas"]["RecordingCaseExportedEventPayload"] | components["schemas"]["RecordingReplayLinkedEventPayload"] | components["schemas"]["RecordingReplayStartedEventPayload"] | components["schemas"]["RecordingReplayCompletedEventPayload"] | components["schemas"]["RecordingBridgeCleanupFailedEventPayload"] | components["schemas"]["RecordingAnalysisStatusEventPayload"] | components["schemas"]["RecordingAnalysisBundleLoadedEventPayload"] | components["schemas"]["RecordingAnalysisStepEventPayload"] | components["schemas"]["GenericOperationEventPayload"] | null;
            /** Event Type */
            event_type: string;
            /** Message */
            message?: string | null;
            /** Operation Id */
            operation_id: string;
            /** Parent Operation Id */
            parent_operation_id?: string | null;
            /** Plan Id */
            plan_id?: string | null;
            /** Seq */
            seq: number;
            /** Summary */
            summary?: string | null;
            /** Timeline Phase */
            timeline_phase?: string | null;
            /** Timeline Scope */
            timeline_scope?: string | null;
            /** Timestamp */
            timestamp: string;
        };
        /** OperationEventsData */
        OperationEventsData: {
            /** After Seq */
            after_seq: number;
            /** Items */
            items?: components["schemas"]["OperationEventItemData"][];
            /** Limit */
            limit: number;
            /** Next After Seq */
            next_after_seq: number;
            /** Operation Id */
            operation_id: string;
        };
        /** OperationInterruptedEventPayload */
        OperationInterruptedEventPayload: {
            /** Command */
            command?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** OperationListData */
        OperationListData: {
            /** Items */
            items?: components["schemas"]["OperationSummaryData"][];
            /**
             * Limit
             * @default 20
             */
            limit: number;
            /**
             * Offset
             * @default 0
             */
            offset: number;
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** OperationProgressData */
        OperationProgressData: {
            /** Agent Role */
            agent_role?: string | null;
            /** Analysis Status */
            analysis_status?: string | null;
            /** App Id */
            app_id?: string | null;
            /** Background Mode */
            background_mode?: string | null;
            /** Batch Kind */
            batch_kind?: string | null;
            /** Bridge Status */
            bridge_status?: string | null;
            /** Case Count */
            case_count?: number | null;
            /** Case Id */
            case_id?: string | null;
            /** Case Index */
            case_index?: number | null;
            /** Case Title */
            case_title?: string | null;
            /** Completed Case Count */
            completed_case_count?: number | null;
            /** Completed Cases */
            completed_cases?: number | null;
            /** Completed Children */
            completed_children?: number | null;
            /** Completed Steps */
            completed_steps?: number | null;
            /** Current Case Id */
            current_case_id?: string | null;
            /** Current Child Case Id */
            current_child_case_id?: string | null;
            /** Current Child Operation Id */
            current_child_operation_id?: string | null;
            /** Current Child Plan Id */
            current_child_plan_id?: string | null;
            /** Current Child Title */
            current_child_title?: string | null;
            /** Current Step Seq */
            current_step_seq?: number | null;
            /** Detached Pid */
            detached_pid?: number | null;
            /** Event Timestamp */
            event_timestamp?: string | null;
            interactive_session?: components["schemas"]["InteractiveSessionStateData"] | null;
            /** Last Case Id */
            last_case_id?: string | null;
            /** Last Child Case Id */
            last_child_case_id?: string | null;
            /** Last Child Operation Id */
            last_child_operation_id?: string | null;
            /** Last Child Plan Id */
            last_child_plan_id?: string | null;
            /** Last Child Title */
            last_child_title?: string | null;
            /** Last Event Type */
            last_event_type?: string | null;
            /** Latest Event Count */
            latest_event_count?: number | null;
            /** Latest Frame Seq */
            latest_frame_seq?: number | null;
            /** Latest Timeline Count */
            latest_timeline_count?: number | null;
            /** Lifecycle State */
            lifecycle_state?: string | null;
            /** Manual Case Count */
            manual_case_count?: number | null;
            /** Phase */
            phase?: string | null;
            /** Plan Event Type */
            plan_event_type?: string | null;
            /** Plan Id */
            plan_id?: string | null;
            /** Plan Name */
            plan_name?: string | null;
            /** Plan Path */
            plan_path?: string | null;
            /** Planner Case Count */
            planner_case_count?: number | null;
            /** Recording Id */
            recording_id?: string | null;
            /** Replay Operation Id */
            replay_operation_id?: string | null;
            /** Review Hint Enabled */
            review_hint_enabled?: boolean | null;
            /** Review Required Case Count */
            review_required_case_count?: number | null;
            /** Snapshot Path */
            snapshot_path?: string | null;
            /** Source Recording Case Path */
            source_recording_case_path?: string | null;
            /** Stage */
            stage?: string | null;
            /** Status */
            status?: string | null;
            /** Target Case Count */
            target_case_count?: number | null;
            /** Total Cases */
            total_cases?: number | null;
            /** Total Children */
            total_children?: number | null;
            /** Total Steps */
            total_steps?: number | null;
            /** Updated At */
            updated_at?: string | null;
            /** Verification Verdict */
            verification_verdict?: string | null;
            /** Verify Change Event Type */
            verify_change_event_type?: string | null;
        };
        /** OperationStartedEventPayload */
        OperationStartedEventPayload: {
            /** Case Id */
            case_id?: string | null;
            /** Case Title */
            case_title?: string | null;
            /** Command */
            command?: string | null;
            /** Operation Id */
            operation_id?: string | null;
            /** Parent Operation Id */
            parent_operation_id?: string | null;
            /** Pid */
            pid?: number | null;
            /** Plan Id */
            plan_id?: string | null;
            /** Position Label */
            position_label?: string | null;
            /** Title */
            title?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** OperationSubmissionData */
        OperationSubmissionData: {
            /** App Id */
            app_id?: string | null;
            execution_result?: components["schemas"]["ExecutedPlanResult"] | null;
            /** Operation Id */
            operation_id: string;
            /** Phase */
            phase?: string | null;
            /** Plan Id */
            plan_id?: string | null;
            /** Plan Name */
            plan_name?: string | null;
            plan_result?: components["schemas"]["GeneratedPlanResult"] | null;
            /** Status */
            status: string;
            /** Verification Verdict */
            verification_verdict?: string | null;
        };
        /** OperationSubmittedEventPayload */
        OperationSubmittedEventPayload: {
            /** Mode */
            mode?: string | null;
            /** Pid */
            pid?: number | null;
        } & {
            [key: string]: unknown;
        };
        /** OperationSummaryData */
        OperationSummaryData: {
            /** App Id */
            app_id?: string | null;
            /** Batch Id */
            batch_id?: string | null;
            /** Case Id */
            case_id?: string | null;
            /** Created At */
            created_at: string;
            /** Device Ref */
            device_ref?: string | null;
            /** Error Code */
            error_code?: string | null;
            /** Error Message */
            error_message?: string | null;
            /** Finished At */
            finished_at?: string | null;
            /** Kind */
            kind: string;
            /** Operation Id */
            operation_id: string;
            /** Parent Operation Id */
            parent_operation_id?: string | null;
            /** Phase */
            phase?: string | null;
            /** Plan Id */
            plan_id?: string | null;
            /** Platform */
            platform?: string | null;
            /** Position Index */
            position_index?: number | null;
            /** Position Label */
            position_label?: string | null;
            /** Run Type */
            run_type?: string | null;
            /** Source Recording Id */
            source_recording_id?: string | null;
            /** Started At */
            started_at?: string | null;
            /** Status */
            status: string;
            /** Target Label */
            target_label?: string | null;
            /** Title */
            title?: string | null;
            /** Verification Verdict */
            verification_verdict?: string | null;
        };
        /** OptimizeCaseOperationResultPayload */
        OptimizeCaseOperationResultPayload: {
            /**
             * Applied
             * @default false
             */
            applied: boolean;
            /** Artifacts */
            artifacts: {
                [key: string]: string;
            };
            /** Confidence */
            confidence?: number | null;
            /** Field Diff Artifact Path */
            field_diff_artifact_path: string;
            /** Field Diffs */
            field_diffs: {
                [key: string]: unknown;
            }[];
            /** Optimization Diagnostics Path */
            optimization_diagnostics_path: string;
            /** Optimization Request Path */
            optimization_request_path: string;
            /** Optimization Result Path */
            optimization_result_path: string;
            /** Patched Fields */
            patched_fields: string[];
            /** Skip Reason */
            skip_reason?: string | null;
            /** Summary */
            summary: string;
        };
        /** OptimizeTimelineEventPayload */
        OptimizeTimelineEventPayload: {
            /** Agent Role */
            agent_role?: string | null;
            /** Applied */
            applied?: boolean | null;
            /** Attempt Count */
            attempt_count?: number | null;
            /** Error Type */
            error_type?: string | null;
            /** Event Timestamp */
            event_timestamp?: string | null;
            /** Lifecycle State */
            lifecycle_state?: string | null;
            /** Patched Field Count */
            patched_field_count?: number | null;
            /** Patched Field Summaries */
            patched_field_summaries?: string[] | null;
            /** Patched Fields */
            patched_fields?: string[] | null;
            /** Request Path */
            request_path?: string | null;
            /** Skip Reason */
            skip_reason?: string | null;
            /** Skipped Field Count */
            skipped_field_count?: number | null;
            /** Step Screen Count */
            step_screen_count?: number | null;
            /** Step Summary Count */
            step_summary_count?: number | null;
            /** Step Transition Count */
            step_transition_count?: number | null;
            /** Timestamp */
            timestamp?: string | null;
            /** Tool Call Count */
            tool_call_count?: number | null;
            /** Tool Calls */
            tool_calls?: string[] | null;
            /** Tool Index */
            tool_index?: number | null;
            /** Tool Name */
            tool_name?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** OrchestrationConfigEditor */
        OrchestrationConfigEditor: {
            /**
             * Allow Retry On Failed
             * @default true
             */
            allow_retry_on_failed: boolean;
            /**
             * Allow Retry On Inconclusive
             * @default true
             */
            allow_retry_on_inconclusive: boolean;
            /**
             * Escalate After Max Attempts
             * @default false
             */
            escalate_after_max_attempts: boolean;
            /**
             * Max Retry Attempts
             * @default 0
             */
            max_retry_attempts: number;
        };
        /** PerceptionCompletedEventPayload */
        PerceptionCompletedEventPayload: {
            /** Element Count */
            element_count: number;
            /** Icon Conf */
            icon_conf?: number | null;
            /** Step */
            step: number;
            /** Tree Available */
            tree_available?: boolean | null;
            /** Tree Node Count */
            tree_node_count?: number | null;
        } & {
            [key: string]: unknown;
        };
        /** PhasedOperationResult */
        PhasedOperationResult: {
            /** App Id */
            app_id: string;
            execution_result?: components["schemas"]["ExecutedPlanResult"] | null;
            execution_usage?: components["schemas"]["TokenUsage"] | null;
            /**
             * Phase
             * @enum {string}
             */
            phase: "planned" | "executed";
            /** Plan Id */
            plan_id: string;
            /** Plan Name */
            plan_name?: string | null;
            plan_result: components["schemas"]["GeneratedPlanResult"];
            planning_usage?: components["schemas"]["TokenUsage"] | null;
            total_usage?: components["schemas"]["TokenUsage"] | null;
        };
        /** PlanCaseExecutionItem */
        PlanCaseExecutionItem: {
            /** Case Id */
            case_id: string;
            /** Error Message */
            error_message?: string | null;
            /**
             * Execution Status
             * @enum {string}
             */
            execution_status: "completed" | "failed" | "incomplete";
            /** Judge Summary */
            judge_summary?: string | null;
            /** Operation Id */
            operation_id?: string | null;
            /**
             * Run Dir
             * Format: path
             */
            run_dir: string;
            /** Status */
            status?: string | null;
            /** Stop Reason */
            stop_reason?: string | null;
            /** Title */
            title: string;
            token_usage?: components["schemas"]["TokenUsage"] | null;
            /**
             * Verdict
             * @enum {string}
             */
            verdict: "passed" | "failed" | "inconclusive";
        };
        /** PlanCaseReorderRequest */
        PlanCaseReorderRequest: {
            /** Case Ids */
            case_ids: string[];
        };
        /** PlanCliRequest */
        PlanCliRequest: {
            /** App Id */
            app_id: string;
            /** Artifact Path */
            artifact_path?: string | null;
            /** Artifact Url */
            artifact_url?: string | null;
            /** Assets Root */
            assets_root?: string | null;
            /**
             * Auto Run
             * @default false
             */
            auto_run: boolean;
            /** Device Ref */
            device_ref?: string | null;
            /** Package */
            package?: string | null;
            /**
             * Requirement Doc Path
             * Format: path
             */
            requirement_doc_path: string;
            /** Runtime Overrides */
            runtime_overrides?: {
                [key: string]: string | number | boolean;
            };
            /** Technical Doc Path */
            technical_doc_path?: string | null;
            /** User Prompt */
            user_prompt?: string | null;
        };
        /** PlanDetailData */
        PlanDetailData: {
            /** App Id */
            app_id: string;
            /**
             * Case Count
             * @default 0
             */
            case_count: number;
            /** Cases */
            cases?: components["schemas"]["CaseBriefData"][];
            /** Plan Id */
            plan_id: string;
            /** Plan Name */
            plan_name?: string | null;
            /** Source */
            source: string;
            /** Version */
            version: string;
        };
        /** PlanImportData */
        PlanImportData: {
            /** App Id */
            app_id: string;
            /**
             * Case Count
             * @default 0
             */
            case_count: number;
            /** Plan Id */
            plan_id: string;
            /** Plan Name */
            plan_name?: string | null;
            /** Plan Path */
            plan_path: string;
            /** Source */
            source: string;
            /** Version */
            version: string;
        };
        /** PlanImportRequest */
        PlanImportRequest: {
            /** App Id */
            app_id: string;
            /** File Name */
            file_name?: string | null;
            /** Name */
            name: string;
            /** Raw Plan */
            raw_plan: {
                [key: string]: unknown;
            };
        };
        /** PlanLatestRunSummaryData */
        PlanLatestRunSummaryData: {
            /** Created At */
            created_at: string;
            /** Finished At */
            finished_at?: string | null;
            /** Operation Id */
            operation_id: string;
            /** Started At */
            started_at?: string | null;
            /** Status */
            status: string;
            /** Verification Verdict */
            verification_verdict?: string | null;
        };
        /** PlanListData */
        PlanListData: {
            /** Items */
            items?: components["schemas"]["PlanListItemData"][];
            /**
             * Limit
             * @default 20
             */
            limit: number;
            /**
             * Offset
             * @default 0
             */
            offset: number;
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** PlanListItemData */
        PlanListItemData: {
            /** App Id */
            app_id: string;
            /**
             * Case Count
             * @default 0
             */
            case_count: number;
            latest_run?: components["schemas"]["PlanLatestRunSummaryData"] | null;
            /** Plan Id */
            plan_id: string;
            /** Plan Name */
            plan_name?: string | null;
            /** Source */
            source: string;
            /** Updated At */
            updated_at: string;
            /** Version */
            version: string;
        };
        /** PlanningTimelineEventPayload */
        PlanningTimelineEventPayload: {
            /** App Id */
            app_id?: string | null;
            /** Assets Root */
            assets_root?: string | null;
            /** Case Count */
            case_count?: number | null;
            /** Case Id */
            case_id?: string | null;
            /** Case Index */
            case_index?: number | null;
            /** Case Title */
            case_title?: string | null;
            /** Completed Case Count */
            completed_case_count?: number | null;
            /** Duplicate Titles */
            duplicate_titles?: string[] | null;
            /** Has Requirement Doc */
            has_requirement_doc?: boolean | null;
            /** Has Review Contract */
            has_review_contract?: boolean | null;
            /** Has Technical Doc */
            has_technical_doc?: boolean | null;
            /** Plan Id */
            plan_id?: string | null;
            /** Plan Path */
            plan_path?: string | null;
            planning_usage?: components["schemas"]["TokenUsage"] | null;
            /** Snapshot Path */
            snapshot_path?: string | null;
            /** Target Case Count */
            target_case_count?: number | null;
            /** Uncovered Indices */
            uncovered_indices?: number[] | null;
        };
        /** PointerForwardingPayload */
        PointerForwardingPayload: {
            /** End X */
            end_x: number;
            /** End Y */
            end_y: number;
            /** Height */
            height: number;
            /** Pointer Id */
            pointer_id: number;
            /** Start X */
            start_x: number;
            /** Start Y */
            start_y: number;
            /** Width */
            width: number;
        };
        /** PointerStepPayload */
        PointerStepPayload: {
            /** Pointer Id */
            pointer_id: number;
            /** X */
            x: number;
            /** Y */
            y: number;
        };
        /** PolicyKnowledgeCandidateDraft */
        PolicyKnowledgeCandidateDraft: {
            /** App Id */
            app_id: string;
            /** Card Id */
            card_id?: string | null;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            card_type: "policy";
            /** Confidence */
            confidence: number;
            payload: components["schemas"]["PolicyPayload"];
            source: components["schemas"]["KnowledgeSource"];
            /** Title */
            title: string;
        };
        /** PolicyKnowledgeCard */
        PolicyKnowledgeCard: {
            /** App Id */
            app_id: string;
            /** Card Id */
            card_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            card_type: "policy";
            /** Confidence */
            confidence: number;
            payload: components["schemas"]["PolicyPayload"];
            source: components["schemas"]["KnowledgeSource"];
            /**
             * Status
             * @enum {string}
             */
            status: "active" | "deprecated" | "archived";
            /** Title */
            title: string;
            /** Updated At */
            updated_at: string;
        };
        /** PolicyKnowledgeCardInput */
        PolicyKnowledgeCardInput: {
            /** App Id */
            app_id: string;
            /** Card Id */
            card_id?: string | null;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            card_type: "policy";
            /** Confidence */
            confidence: number;
            payload: components["schemas"]["PolicyPayload"];
            source: components["schemas"]["KnowledgeSource"];
            /**
             * Status
             * @default active
             * @enum {string}
             */
            status: "active" | "deprecated" | "archived";
            /** Title */
            title: string;
        };
        /** PolicyPayload */
        PolicyPayload: {
            /** Environment Rules */
            environment_rules?: string[];
            /** Permission Rules */
            permission_rules?: string[];
            /** Platform Constraints */
            platform_constraints?: string[];
            /** Risk Controls */
            risk_controls?: string[];
        };
        /** PostRunChildOperationEventPayload */
        PostRunChildOperationEventPayload: {
            /** Case Id */
            case_id: string;
            /** Child Kind */
            child_kind: string;
            /** Error */
            error?: string | null;
            /** Judge Result Path */
            judge_result_path?: string | null;
            /** Operation Id */
            operation_id?: string | null;
            /** Optimization Fields */
            optimization_fields?: string[];
            /** Request Path */
            request_path?: string | null;
            /** Source Attempt Index */
            source_attempt_index?: number | null;
            /** Trigger Signals */
            trigger_signals?: string[];
            /** Trigger Source */
            trigger_source?: string | null;
        };
        /** ProxyConfigEditor */
        ProxyConfigEditor: {
            /**
             * Enabled
             * @default false
             */
            enabled: boolean;
            /** No Proxy */
            no_proxy?: string[];
            /** Url */
            url?: string | null;
        };
        /** RecordInteractionRequest */
        RecordInteractionRequest: {
            /** Client Command Id */
            client_command_id: string;
            forwarding_ack: components["schemas"]["ForwardingAckRequest"];
            /**
             * Kind
             * @enum {string}
             */
            kind: "click" | "swipe" | "input" | "back";
            /** Payload */
            payload?: {
                [key: string]: unknown;
            };
            /**
             * Source
             * @default scrcpy_bridge
             */
            source: string;
        };
        /** RecordedCurrentAppState */
        RecordedCurrentAppState: {
            /** Entry Identity */
            entry_identity?: string | null;
            /** Load State */
            load_state?: string | null;
            /** Platform */
            platform?: string | null;
            /** Raw */
            raw?: {
                [key: string]: unknown;
            };
            /** Surface Identity */
            surface_identity?: string | null;
            /** Title */
            title?: string | null;
            /** Url */
            url?: string | null;
        };
        /** RecordedInputEvent */
        RecordedInputEvent: {
            /** Event Id */
            event_id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "click" | "swipe" | "input" | "back";
            /** Payload */
            payload?: {
                [key: string]: unknown;
            };
            /** Recording Id */
            recording_id: string;
            /**
             * Source
             * @default scrcpy_bridge
             */
            source: string;
            /** Summary */
            summary?: string | null;
            /** Timestamp */
            timestamp?: string;
        };
        /** RecordingAnalysisActionEvidence */
        RecordingAnalysisActionEvidence: {
            /**
             * Action Kind
             * @enum {string}
             */
            action_kind: "click" | "swipe" | "input" | "back";
            /** After Entry Identity */
            after_entry_identity?: string | null;
            /** After Surface Identity */
            after_surface_identity?: string | null;
            /** Before Entry Identity */
            before_entry_identity?: string | null;
            /** Before Surface Identity */
            before_surface_identity?: string | null;
            /** Raw Action Summary */
            raw_action_summary?: string | null;
            resolved_target?: components["schemas"]["RecordingAnalysisResolvedTarget"] | null;
            /** Target Candidates */
            target_candidates?: components["schemas"]["RecordingAnalysisTargetCandidate"][];
            /** Warnings */
            warnings?: string[];
        };
        /** RecordingAnalysisBundleLoadedEventPayload */
        RecordingAnalysisBundleLoadedEventPayload: {
            /** Recording Id */
            recording_id: string;
            /** Total Steps */
            total_steps: number;
        };
        /** RecordingAnalysisData */
        RecordingAnalysisData: {
            analysis: components["schemas"]["RecordingAnalysisResult"];
            operation?: components["schemas"]["OperationSubmissionData"] | null;
        };
        /** RecordingAnalysisOutcomeEvidence */
        RecordingAnalysisOutcomeEvidence: {
            /** After Entry Identity */
            after_entry_identity?: string | null;
            /** After Surface Identity */
            after_surface_identity?: string | null;
            /** Before Entry Identity */
            before_entry_identity?: string | null;
            /** Before Surface Identity */
            before_surface_identity?: string | null;
            /** Screen Diff */
            screen_diff?: {
                [key: string]: unknown;
            };
            /** Screen Diff Summary */
            screen_diff_summary?: string | null;
            /** Warnings */
            warnings?: string[];
        };
        /** RecordingAnalysisResolvedTarget */
        RecordingAnalysisResolvedTarget: {
            /** Bounds */
            bounds?: number[] | null;
            /** Class Name */
            class_name?: string | null;
            /** Confidence */
            confidence?: number | null;
            /** Content Desc */
            content_desc?: string | null;
            /** Kind */
            kind?: string | null;
            /** Label */
            label?: string | null;
            /** Linked Tree Node Id */
            linked_tree_node_id?: string | null;
            /** Resource Id */
            resource_id?: string | null;
            /** Semantic Role */
            semantic_role?: string | null;
            /** Source */
            source?: string | null;
            /** Stable Key */
            stable_key?: string | null;
            /** State */
            state?: {
                [key: string]: unknown;
            };
        };
        /** RecordingAnalysisResult */
        RecordingAnalysisResult: {
            /**
             * Export Ready
             * @default false
             */
            export_ready: boolean;
            /** Failure Reason */
            failure_reason?: string | null;
            /** Recording Id */
            recording_id: string;
            /** Source Summary */
            source_summary?: string | null;
            /**
             * Status
             * @default pending
             * @enum {string}
             */
            status: "pending" | "completed" | "failed";
            /** Steps */
            steps?: components["schemas"]["RecordingAnalysisStep"][];
            test_case?: components["schemas"]["TestCase"] | null;
            /** Warnings */
            warnings?: string[];
        };
        /** RecordingAnalysisScreenshotRef */
        RecordingAnalysisScreenshotRef: {
            compact_tree_excerpt?: components["schemas"]["RecordingAnalysisTreeExcerpt"] | null;
            /** Entry Id */
            entry_id: string;
            /** Entry Identity */
            entry_identity?: string | null;
            /** Observation Id */
            observation_id: string;
            /**
             * Path
             * Format: path
             */
            path: string;
            /** Recording Id */
            recording_id: string;
            /**
             * Role
             * @enum {string}
             */
            role: "before" | "after";
            /** Seq */
            seq: number;
            /** Summary */
            summary?: string | null;
            /** Surface Identity */
            surface_identity?: string | null;
            /**
             * Tree Available
             * @default false
             */
            tree_available: boolean;
            /** Tree Evidence Id */
            tree_evidence_id?: string | null;
        };
        /** RecordingAnalysisStatusEventPayload */
        RecordingAnalysisStatusEventPayload: {
            /** Analysis Status */
            analysis_status?: string | null;
            /** Recording Id */
            recording_id: string;
        };
        /** RecordingAnalysisStep */
        RecordingAnalysisStep: {
            /** Action */
            action?: string | null;
            action_evidence?: components["schemas"]["RecordingAnalysisActionEvidence"] | null;
            /** After Observation Id */
            after_observation_id: string;
            after_screenshot: components["schemas"]["RecordingAnalysisScreenshotRef"];
            /** Before Observation Id */
            before_observation_id: string;
            before_screenshot: components["schemas"]["RecordingAnalysisScreenshotRef"];
            /** Entry Id */
            entry_id: string;
            /** Intent */
            intent?: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "click" | "swipe" | "input" | "back";
            outcome_evidence?: components["schemas"]["RecordingAnalysisOutcomeEvidence"] | null;
            /** Procedure Step */
            procedure_step?: string | null;
            /** Recording Id */
            recording_id: string;
            /** Seq */
            seq: number;
            /** State Change */
            state_change?: string | null;
            /** Summary */
            summary?: string | null;
            /** Warnings */
            warnings?: string[];
        };
        /** RecordingAnalysisStepEventPayload */
        RecordingAnalysisStepEventPayload: {
            /** Completed Steps */
            completed_steps?: number | null;
            /** Current Step Seq */
            current_step_seq?: number | null;
            /** Recording Id */
            recording_id: string;
            /** Total Steps */
            total_steps?: number | null;
        };
        /** RecordingAnalysisTargetCandidate */
        RecordingAnalysisTargetCandidate: {
            /** Bounds */
            bounds?: number[] | null;
            /** Class Name */
            class_name?: string | null;
            /** Confidence */
            confidence?: number | null;
            /** Content Desc */
            content_desc?: string | null;
            /** Kind */
            kind?: string | null;
            /** Label */
            label?: string | null;
            /** Linked Tree Node Id */
            linked_tree_node_id?: string | null;
            /**
             * Rank
             * @default 0
             */
            rank: number;
            /** Resource Id */
            resource_id?: string | null;
            /** Semantic Role */
            semantic_role?: string | null;
            /** Source */
            source?: string | null;
            /** Stable Key */
            stable_key?: string | null;
            /** State */
            state?: {
                [key: string]: unknown;
            };
        };
        /** RecordingAnalysisTreeExcerpt */
        RecordingAnalysisTreeExcerpt: {
            /** Compact Nodes */
            compact_nodes?: components["schemas"]["RecordingAnalysisTreeNode"][];
            /** Focus Hits */
            focus_hits?: components["schemas"]["RecordingAnalysisTreeFocusHit"][];
            /**
             * Node Count
             * @default 0
             */
            node_count: number;
        };
        /** RecordingAnalysisTreeFocusHit */
        RecordingAnalysisTreeFocusHit: {
            /** Label */
            label: string;
            /** Node Id */
            node_id?: string | null;
            /** Score */
            score: number;
        };
        /** RecordingAnalysisTreeNode */
        RecordingAnalysisTreeNode: {
            /** Bounds */
            bounds?: number[] | null;
            /** Class Name */
            class_name?: string | null;
            /** Content Desc */
            content_desc?: string | null;
            /** Node Id */
            node_id: string;
            /** Parent Id */
            parent_id?: string | null;
            /** Resource Id */
            resource_id?: string | null;
            /** Stable Key */
            stable_key?: string | null;
            /** State */
            state?: {
                [key: string]: unknown;
            };
            /** Text */
            text?: string | null;
        };
        /** RecordingBeginData */
        RecordingBeginData: {
            bridge: components["schemas"]["RecordingBridgeInfo"];
            session: components["schemas"]["RecordingSession"];
        };
        /** RecordingBridgeCleanupFailedEventPayload */
        RecordingBridgeCleanupFailedEventPayload: {
            /** Error */
            error: string;
            /** Recording Id */
            recording_id: string;
            /** Status */
            status: string;
        };
        /** RecordingBridgeInfo */
        RecordingBridgeInfo: {
            /** Base Url */
            base_url: string;
            /** Recording Id */
            recording_id: string;
            /** Ws Url */
            ws_url: string;
        };
        /** RecordingCaseExport */
        RecordingCaseExport: {
            /**
             * Analysis Path
             * Format: path
             */
            analysis_path: string;
            /** Case Id */
            case_id: string;
            /**
             * Case Path
             * Format: path
             */
            case_path: string;
            /** Exported At */
            exported_at?: string;
            /** Plan Id */
            plan_id?: string | null;
            /** Plan Path */
            plan_path?: string | null;
            /** Recording Id */
            recording_id: string;
            /** Snapshot Path */
            snapshot_path?: string | null;
        };
        /** RecordingCaseExportedEventPayload */
        RecordingCaseExportedEventPayload: {
            /** Case Id */
            case_id: string;
            /** Case Path */
            case_path: string;
            /** Plan Id */
            plan_id?: string | null;
            /** Plan Path */
            plan_path?: string | null;
            /** Recording Id */
            recording_id: string;
        };
        /** RecordingCreateData */
        RecordingCreateData: {
            session: components["schemas"]["RecordingSession"];
        };
        /** RecordingExportData */
        RecordingExportData: {
            analysis: components["schemas"]["RecordingAnalysisResult"];
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            };
            case: components["schemas"]["RecordingCaseExport"];
        };
        /** RecordingGetData */
        RecordingGetData: {
            /** Events */
            events?: components["schemas"]["RecordedInputEvent"][];
            session: components["schemas"]["RecordingSession"];
            /** Timeline */
            timeline?: components["schemas"]["TimelineEntry"][];
        };
        /** RecordingIdEventPayload */
        RecordingIdEventPayload: {
            /** Recording Id */
            recording_id: string;
        };
        /** RecordingInteractionData */
        RecordingInteractionData: {
            entry: components["schemas"]["TimelineEntry"];
        };
        /** RecordingInteractionRecordedEventPayload */
        RecordingInteractionRecordedEventPayload: {
            /** After Observation Id */
            after_observation_id?: string | null;
            /** After Stabilized */
            after_stabilized?: boolean | null;
            /** Before Observation Id */
            before_observation_id?: string | null;
            /** Entry Id */
            entry_id: string;
            /** Forwarding Event Id */
            forwarding_event_id?: string | null;
            /** Kind */
            kind: string;
            /** Recording Event Id */
            recording_event_id?: string | null;
        };
        /** RecordingObservationData */
        RecordingObservationData: {
            observation: components["schemas"]["ObservationSnapshot"];
        };
        /** RecordingReplayCompletedEventPayload */
        RecordingReplayCompletedEventPayload: {
            /** Case Id */
            case_id: string;
            /** Recording Id */
            recording_id: string;
            /** Run Dir */
            run_dir: string;
            /** Verdict */
            verdict?: string | null;
        };
        /** RecordingReplayData */
        RecordingReplayData: {
            replay: components["schemas"]["RecordingReplayResult"];
        };
        /** RecordingReplayLinkedEventPayload */
        RecordingReplayLinkedEventPayload: {
            /** Operation Id */
            operation_id: string;
            /** Recording Id */
            recording_id: string;
            /** Verdict */
            verdict?: string | null;
        };
        /** RecordingReplayOperationResult */
        RecordingReplayOperationResult: {
            /** App Id */
            app_id?: string | null;
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            };
            /**
             * Attempt Count
             * @default 0
             */
            attempt_count: number;
            /** Attempts */
            attempts?: components["schemas"]["CaseExecutionAttempt"][];
            /** Case Id */
            case_id: string;
            /** Confidence */
            confidence?: number | null;
            /** Current Step */
            current_step?: string | null;
            /** Event History */
            event_history?: {
                [key: string]: unknown;
            }[];
            /** Evidence */
            evidence?: (components["schemas"]["JudgeExecutionEvidence"] | components["schemas"]["JudgeEventEvidence"] | components["schemas"]["JudgeDecisionTraceEvidence"] | components["schemas"]["JudgeRunnerHistoryEvidence"] | components["schemas"]["JudgeRunnerMemoryEvidence"] | components["schemas"]["JudgeRunnerIssueEvidence"] | components["schemas"]["JudgeRuntimeErrorLogEvidence"] | components["schemas"]["JudgeScreenFrameEvidence"] | components["schemas"]["JudgeScreenDiffEvidence"] | components["schemas"]["JudgeScreenshotEvidence"])[];
            execution: components["schemas"]["ExecutionOutcome"];
            /** Failure Hypothesis */
            failure_hypothesis?: string | null;
            /** Final Decision */
            final_decision?: {
                [key: string]: unknown;
            } | null;
            /** Judge Reason */
            judge_reason?: string | null;
            /** Metadata */
            metadata?: {
                [key: string]: unknown;
            };
            /** Missing Evidence */
            missing_evidence?: string[];
            /** Plan Id */
            plan_id: string;
            /** Recording Id */
            recording_id: string;
            /**
             * Run Dir
             * Format: path
             */
            run_dir: string;
            /**
             * Schema Version
             * @default phase8.orchestrated_case_execution_result.v1
             */
            schema_version: string;
            /**
             * Status
             * @default finished
             * @enum {string}
             */
            status: "pending" | "ready" | "running" | "needs_retry" | "escalated" | "finished";
            /** Summary */
            summary?: string | null;
            /** Supplemental Context */
            supplemental_context?: string[];
            /** Supporting Evidence Ids */
            supporting_evidence_ids?: string[];
            token_usage?: components["schemas"]["TokenUsage"] | null;
            /**
             * Verdict
             * @enum {string}
             */
            verdict: "passed" | "failed" | "inconclusive";
        };
        /** RecordingReplayResult */
        RecordingReplayResult: {
            /**
             * Artifact Manifest Path
             * Format: path
             */
            artifact_manifest_path: string;
            /** Case Id */
            case_id: string;
            /** Operation Id */
            operation_id: string;
            /** Recording Id */
            recording_id: string;
            /** Replayed At */
            replayed_at?: string;
            /**
             * Result Path
             * Format: path
             */
            result_path: string;
            /**
             * Run Dir
             * Format: path
             */
            run_dir: string;
            /**
             * Verdict
             * @enum {string}
             */
            verdict: "passed" | "failed" | "inconclusive";
        };
        /** RecordingReplayStartedEventPayload */
        RecordingReplayStartedEventPayload: {
            /** Case Id */
            case_id: string;
            /** Recording Id */
            recording_id: string;
        };
        /** RecordingSession */
        RecordingSession: {
            /** App Id */
            app_id: string;
            app_target: components["schemas"]["AppTarget"];
            /**
             * Asset Dir
             * Format: path
             */
            asset_dir: string;
            /** Case Id */
            case_id?: string | null;
            /** Created At */
            created_at?: string;
            /** Device Ref */
            device_ref?: string | null;
            /** Failure Reason */
            failure_reason?: string | null;
            /** Finished At */
            finished_at?: string | null;
            /** Latest Frame Seq */
            latest_frame_seq?: number | null;
            /** Recording Id */
            recording_id: string;
            /** Started At */
            started_at?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "created" | "recording" | "stopped" | "cancelled" | "failed";
        };
        /** RecordingSessionData */
        RecordingSessionData: {
            session: components["schemas"]["RecordingSession"];
        };
        /** RecordingSessionTerminalResult */
        RecordingSessionTerminalResult: {
            /** Recording Id */
            recording_id: string;
            /** Status */
            status: string;
        };
        /** RecordingStartedEventPayload */
        RecordingStartedEventPayload: {
            /** Bridge Ws Url */
            bridge_ws_url: string;
            /** Recording Id */
            recording_id: string;
        };
        /** RecordingTapData */
        RecordingTapData: {
            event: components["schemas"]["RecordedInputEvent"];
        };
        /** RecordingTapObservedEventPayload */
        RecordingTapObservedEventPayload: {
            /** Event Id */
            event_id: string;
            /** Kind */
            kind: string;
            /** Payload */
            payload: {
                [key: string]: unknown;
            };
        };
        /** RecordingTimelineData */
        RecordingTimelineData: {
            /** Timeline */
            timeline?: components["schemas"]["TimelineEntry"][];
        };
        /** ReproduceOperationData */
        ReproduceOperationData: {
            /** Artifact Groups */
            artifact_groups?: components["schemas"]["RunArtifactGroupData"][];
            /** Artifact Manifest Path */
            artifact_manifest_path?: string | null;
            /** Artifact Manifest Version */
            artifact_manifest_version?: number | null;
            /** Attempt Usages */
            attempt_usages?: components["schemas"]["AttemptTokenUsageData"][];
            /** Case Runs */
            case_runs?: components["schemas"]["CaseRunArtifactSummaryData"][];
            /** Conflict Reason */
            conflict_reason?: string | null;
            /** Device Ref */
            device_ref?: string | null;
            /** Diagnostics Path */
            diagnostics_path?: string | null;
            /** Duration Ms */
            duration_ms?: number | null;
            execution_usage?: components["schemas"]["TokenUsageData"] | null;
            /** Failure Category */
            failure_category?: string | null;
            /** Operation Id */
            operation_id: string;
            /** Phase */
            phase?: string | null;
            planning_usage?: components["schemas"]["TokenUsageData"] | null;
            /** Platform */
            platform?: string | null;
            /** Primary Artifact Ids */
            primary_artifact_ids?: string[];
            /** Primary Artifacts */
            primary_artifacts?: components["schemas"]["RunArtifactItemData"][];
            /** Repro Dir */
            repro_dir?: string | null;
            /** Reproduction Entries */
            reproduction_entries?: components["schemas"]["ReproductionEntry"][];
            /** Resource Scope */
            resource_scope?: string | null;
            /** Run Type */
            run_type?: string | null;
            schema_versions?: components["schemas"]["ArtifactSchemaVersions"];
            /** Source Recording Id */
            source_recording_id?: string | null;
            /** Status */
            status: string;
            /** Target Label */
            target_label?: string | null;
            /** Title */
            title?: string | null;
            token_usage?: components["schemas"]["TokenUsageData"] | null;
            upstream_review?: components["schemas"]["UpstreamReviewArtifacts"] | null;
            /** Verification Verdict */
            verification_verdict?: string | null;
            /** Warning Summary */
            warning_summary?: string[];
        };
        /** ReproductionEntry */
        ReproductionEntry: {
            /** Case Id */
            case_id?: string | null;
            /** Command */
            command: string;
            /** Reason */
            reason?: string | null;
            /**
             * Request File
             * Format: path
             */
            request_file: string;
            /** Source Operation Id */
            source_operation_id?: string | null;
            /**
             * Target Kind
             * @enum {string}
             */
            target_kind: "plan" | "run_case" | "run_plan" | "run_plans" | "verify_change" | "review" | "optimize_case" | "knowledge_post_action";
        };
        /** ResourceClaimedEventPayload */
        ResourceClaimedEventPayload: {
            /** Device Ref */
            device_ref?: string | null;
            /** Resource Scope */
            resource_scope?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** ResourceConflictEventPayload */
        ResourceConflictEventPayload: {
            /** Blocking Device Ref */
            blocking_device_ref?: string | null;
            /** Command */
            command?: string | null;
            /** Reason */
            reason?: string | null;
            /** Requested Device Ref */
            requested_device_ref?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** ResourceReleasedEventPayload */
        ResourceReleasedEventPayload: {
            /** Device Ref */
            device_ref?: string | null;
            /** Reason */
            reason?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** ReviewCliRequest */
        ReviewCliRequest: {
            /** App Id */
            app_id?: string | null;
            /** Artifact Path */
            artifact_path?: string | null;
            /** Case Types */
            case_types?: ("best_practice" | "bad_case" | "review_checkpoint")[];
            /** Change Summary */
            change_summary?: string | null;
            /** Changed Files */
            changed_files?: string[];
            /** Diff Text */
            diff_text?: string | null;
            /** Platforms */
            platforms?: ("android" | "ios" | "web")[];
            /** Requirement Doc Path */
            requirement_doc_path?: string | null;
            /** Review Query */
            review_query?: string | null;
            /** Tags */
            tags?: string[];
            /** Technical Doc Path */
            technical_doc_path?: string | null;
        };
        /** ReviewOperationResultPayload */
        ReviewOperationResultPayload: {
            /** App Id */
            app_id?: string | null;
            /** Artifact Manifest Path */
            artifact_manifest_path: string;
            /** Artifact Manifest Version */
            artifact_manifest_version?: number | null;
            /** Artifacts */
            artifacts: {
                [key: string]: string;
            };
            /** Contract Versions */
            contract_versions?: {
                [key: string]: string | null;
            };
            /** Diagnostics Path */
            diagnostics_path?: string | null;
            /** Duration Ms */
            duration_ms?: number | null;
            /** Failure Category */
            failure_category?: string | null;
            /** Finding Count */
            finding_count: number;
            /** High Risk Count */
            high_risk_count: number;
            /** Llm Transcript Path */
            llm_transcript_path?: string | null;
            /** Retrieval Path */
            retrieval_path: string;
            /** Review Orchestration Path */
            review_orchestration_path: string;
            /** Review Request Path */
            review_request_path: string;
            /** Review Result Path */
            review_result_path: string;
            /** Risk Summary */
            risk_summary: string;
            /** Warning Summary */
            warning_summary?: string[];
        };
        /** ReviewTimelineEventPayload */
        ReviewTimelineEventPayload: {
            /** App Id */
            app_id: string;
            /** Finding Count */
            finding_count?: number | null;
            /** Prompt Hit Count */
            prompt_hit_count?: number | null;
            /** Retrieval Hit Count */
            retrieval_hit_count?: number | null;
            /** Root Dir */
            root_dir?: string | null;
            /** Suggested Case Count */
            suggested_case_count?: number | null;
        } & {
            [key: string]: unknown;
        };
        /** RunArtifactChildItemData */
        RunArtifactChildItemData: {
            /** Child Id */
            child_id: string;
            /** Content Url */
            content_url?: string | null;
            /** Media Type */
            media_type?: string | null;
            /** Name */
            name: string;
            /** Path */
            path: string;
            /** Size Bytes */
            size_bytes?: number | null;
        };
        /** RunArtifactChildrenData */
        RunArtifactChildrenData: {
            /** Artifact Id */
            artifact_id: string;
            /** Items */
            items?: components["schemas"]["RunArtifactChildItemData"][];
            /** Kind */
            kind: string;
            /** Operation Id */
            operation_id: string;
            /** Title */
            title: string;
        };
        /** RunArtifactContentData */
        RunArtifactContentData: {
            /** Artifact Id */
            artifact_id: string;
            /** Content */
            content: string;
            /**
             * Encoding
             * @default utf-8
             */
            encoding: string;
            /** Media Type */
            media_type?: string | null;
            /**
             * Truncated
             * @default false
             */
            truncated: boolean;
        };
        /** RunArtifactGroupData */
        RunArtifactGroupData: {
            /** Group Id */
            group_id: string;
            /** Items */
            items?: components["schemas"]["RunArtifactItemData"][];
            /** Title */
            title: string;
        };
        /** RunArtifactItemData */
        RunArtifactItemData: {
            /** Artifact Id */
            artifact_id: string;
            /** Case Id */
            case_id?: string | null;
            /** Content Url */
            content_url?: string | null;
            /** Download Url */
            download_url?: string | null;
            /**
             * Exists
             * @default true
             */
            exists: boolean;
            /** Kind */
            kind: string;
            /** Label */
            label: string;
            /** Media Type */
            media_type?: string | null;
            /** Metadata */
            metadata?: {
                [key: string]: unknown;
            };
            /** Path */
            path: string;
            /** Role */
            role: string;
            /** Scope */
            scope: string;
        };
        /** RunCaseCliRequest */
        RunCaseCliRequest: {
            /** App Id */
            app_id: string;
            app_target?: components["schemas"]["AppTarget"] | null;
            /** Artifact Path */
            artifact_path?: string | null;
            /** Assets Root */
            assets_root?: string | null;
            /** Case Id */
            case_id: string;
            /** Device Ref */
            device_ref?: string | null;
            /** Package */
            package?: string | null;
            /** Plan Id */
            plan_id: string;
            /** Runtime Overrides */
            runtime_overrides?: {
                [key: string]: string | number | boolean;
            };
        };
        /** RunCaseResultData */
        RunCaseResultData: {
            /** App Id */
            app_id?: string | null;
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            };
            /**
             * Attempt Count
             * @default 0
             */
            attempt_count: number;
            /** Attempts */
            attempts?: components["schemas"]["CaseExecutionAttempt"][];
            /** Case Id */
            case_id: string;
            /** Confidence */
            confidence?: number | null;
            /** Current Step */
            current_step?: string | null;
            /** Event History */
            event_history?: {
                [key: string]: unknown;
            }[];
            /** Evidence */
            evidence?: (components["schemas"]["JudgeExecutionEvidence"] | components["schemas"]["JudgeEventEvidence"] | components["schemas"]["JudgeDecisionTraceEvidence"] | components["schemas"]["JudgeRunnerHistoryEvidence"] | components["schemas"]["JudgeRunnerMemoryEvidence"] | components["schemas"]["JudgeRunnerIssueEvidence"] | components["schemas"]["JudgeRuntimeErrorLogEvidence"] | components["schemas"]["JudgeScreenFrameEvidence"] | components["schemas"]["JudgeScreenDiffEvidence"] | components["schemas"]["JudgeScreenshotEvidence"])[];
            execution: components["schemas"]["ExecutionOutcome"];
            /** Failure Hypothesis */
            failure_hypothesis?: string | null;
            /** Final Decision */
            final_decision?: {
                [key: string]: unknown;
            } | null;
            /** Judge Reason */
            judge_reason?: string | null;
            /** Metadata */
            metadata?: {
                [key: string]: unknown;
            };
            /** Missing Evidence */
            missing_evidence?: string[];
            /** Plan Id */
            plan_id: string;
            /** Run Dir */
            run_dir: string;
            /** Schema Version */
            schema_version?: string | null;
            /** Status */
            status?: string | null;
            /** Summary */
            summary?: string | null;
            /** Supplemental Context */
            supplemental_context?: string[];
            /** Supporting Evidence Ids */
            supporting_evidence_ids?: string[];
            /** Verdict */
            verdict: string;
        };
        /** RunFailedEventPayload */
        RunFailedEventPayload: {
            /** Run Dir */
            run_dir: string;
        } & {
            [key: string]: unknown;
        };
        /** RunPlanCliRequest */
        RunPlanCliRequest: {
            /** App Id */
            app_id: string;
            app_target?: components["schemas"]["AppTarget"] | null;
            /** Artifact Path */
            artifact_path?: string | null;
            /** Assets Root */
            assets_root?: string | null;
            /** Base Url */
            base_url?: string | null;
            /** Bundle Id */
            bundle_id?: string | null;
            /** Device Ref */
            device_ref?: string | null;
            /**
             * Fail Fast
             * @default false
             */
            fail_fast: boolean;
            /**
             * Headless
             * @default false
             */
            headless: boolean;
            /** Origin */
            origin?: string | null;
            /** Package */
            package?: string | null;
            /** Plan Id */
            plan_id: string;
            /** Runtime Overrides */
            runtime_overrides?: {
                [key: string]: string | number | boolean;
            };
        };
        /** RunPlanOperationResultPayload */
        RunPlanOperationResultPayload: {
            /** Artifacts */
            artifacts: {
                [key: string]: string;
            };
            /** Failed Cases */
            failed_cases: number;
            /** Inconclusive Cases */
            inconclusive_cases: number;
            /** Items */
            items: components["schemas"]["PlanCaseExecutionItem"][];
            /** Passed Cases */
            passed_cases: number;
            /** Plan Id */
            plan_id: string;
            /** Report Path */
            report_path: string;
            /** Stopped Early */
            stopped_early: boolean;
            /** Summary Path */
            summary_path: string;
            token_usage?: components["schemas"]["TokenUsage"] | null;
            /** Total Cases */
            total_cases: number;
            /**
             * Verification Status
             * @enum {string}
             */
            verification_status: "passed" | "failed" | "inconclusive" | "stopped";
        };
        /** RunPlansAggregate */
        RunPlansAggregate: {
            /** Cancelled Children */
            cancelled_children: number;
            /** Completed Children */
            completed_children: number;
            /** Current Child Operation Id */
            current_child_operation_id?: string | null;
            /** Current Child Plan Id */
            current_child_plan_id?: string | null;
            /** Current Child Title */
            current_child_title?: string | null;
            /** Failed Children */
            failed_children: number;
            /**
             * Interrupted Children
             * @default 0
             */
            interrupted_children: number;
            /** Queued Children */
            queued_children: number;
            /** Running Children */
            running_children: number;
            /** Succeeded Children */
            succeeded_children: number;
            token_usage?: components["schemas"]["TokenUsage"] | null;
            /** Total Children */
            total_children: number;
        };
        /** RunPlansChildSummary */
        RunPlansChildSummary: {
            /** Created At */
            created_at: string;
            /** Error Code */
            error_code?: string | null;
            /** Error Message */
            error_message?: string | null;
            /** Finished At */
            finished_at?: string | null;
            /** Operation Id */
            operation_id: string;
            /** Plan Id */
            plan_id?: string | null;
            /** Position Index */
            position_index?: number | null;
            /** Position Label */
            position_label?: string | null;
            /** Started At */
            started_at?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "running" | "succeeded" | "failed" | "cancelled" | "interrupted";
            /** Title */
            title: string;
            token_usage?: components["schemas"]["TokenUsage"] | null;
            /** Verification Verdict */
            verification_verdict?: ("passed" | "failed" | "inconclusive") | null;
        };
        /** RunPlansCliRequest */
        RunPlansCliRequest: {
            /** App Id */
            app_id: string;
            app_target?: components["schemas"]["AppTarget"] | null;
            /** Artifact Path */
            artifact_path?: string | null;
            /** Assets Root */
            assets_root?: string | null;
            /** Base Url */
            base_url?: string | null;
            /** Bundle Id */
            bundle_id?: string | null;
            /** Device Ref */
            device_ref?: string | null;
            /**
             * Fail Fast
             * @default false
             */
            fail_fast: boolean;
            /**
             * Headless
             * @default false
             */
            headless: boolean;
            /** Origin */
            origin?: string | null;
            /** Package */
            package?: string | null;
            /** Plan Ids */
            plan_ids: string[];
            /** Runtime Overrides */
            runtime_overrides?: {
                [key: string]: string | number | boolean;
            };
        };
        /** RunPlansResultPayload */
        RunPlansResultPayload: {
            aggregate: components["schemas"]["RunPlansAggregate"];
            /** App Id */
            app_id: string;
            /**
             * Batch Kind
             * @default single_device_multi_plan
             * @constant
             */
            batch_kind: "single_device_multi_plan";
            /** Children */
            children: components["schemas"]["RunPlansChildSummary"][];
            /** Completed Children */
            completed_children: number;
            /** Device Ref */
            device_ref?: string | null;
            /** Plan Ids */
            plan_ids: string[];
            /**
             * Stopped Early
             * @default false
             */
            stopped_early: boolean;
            token_usage?: components["schemas"]["TokenUsage"] | null;
            /** Total Children */
            total_children: number;
            /** Verification Verdict */
            verification_verdict?: ("passed" | "failed" | "inconclusive") | null;
        };
        /** RunStartedEventPayload */
        RunStartedEventPayload: {
            /** Case Title */
            case_title?: string | null;
            /** Run Dir */
            run_dir: string;
        } & {
            [key: string]: unknown;
        };
        /** RunStoppedEventPayload */
        RunStoppedEventPayload: {
            /** Action */
            action?: string | null;
            /** Advice */
            advice?: string | null;
            /** Consecutive No Effect Count */
            consecutive_no_effect_count?: number | null;
            /** Consecutive Postcheck Failure Count */
            consecutive_postcheck_failure_count?: number | null;
            /** Postcheck Summary */
            postcheck_summary?: string | null;
            /** Reason */
            reason?: string | null;
            /** Step */
            step?: number | null;
            /** Summary */
            summary?: string | null;
            /** Warning Code */
            warning_code?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** RunnerActionEventPayload */
        RunnerActionEventPayload: {
            /** Action */
            action: string;
            /** Step */
            step?: number | null;
            /** Summary */
            summary?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** RunnerContractMissEventPayload */
        RunnerContractMissEventPayload: {
            /** Attempt */
            attempt: number;
            /** Result Summary */
            result_summary: string;
            /** Seeded Element Count */
            seeded_element_count: number;
            /** Step */
            step?: number | null;
            /** Tool Names */
            tool_names: string[];
            /** Will Retry */
            will_retry: boolean;
        } & {
            [key: string]: unknown;
        };
        /** RunnerDecisionCompletedEventPayload */
        RunnerDecisionCompletedEventPayload: {
            /** Action */
            action: string;
            /** Step */
            step?: number | null;
            /** Summary */
            summary?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** RunnerRuntimeEventPayload */
        RunnerRuntimeEventPayload: {
            /** Agent Role */
            agent_role: string;
            /** Event Timestamp */
            event_timestamp?: string | null;
            /** Lifecycle State */
            lifecycle_state: string;
            /** Root Dir */
            root_dir?: string | null;
            /** Runner Event Type */
            runner_event_type?: string | null;
            /** Timestamp */
            timestamp?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** RunnerToolCalledEventPayload */
        RunnerToolCalledEventPayload: {
            /** Arguments */
            arguments: {
                [key: string]: unknown;
            };
            /** Result Summary */
            result_summary: string;
            /** Step */
            step?: number | null;
            /** Tool Name */
            tool_name: string;
        } & {
            [key: string]: unknown;
        };
        /** RuntimeConfigEditor */
        RuntimeConfigEditor: {
            /** Icon Conf */
            icon_conf?: number | null;
            /** Interval */
            interval?: number | null;
            /** Max Seconds */
            max_seconds?: number | null;
            /** Max Side */
            max_side?: number | null;
            /** Max Steps */
            max_steps?: number | null;
            /** Max Tokens */
            max_tokens?: number | null;
            /** Runner Include Screenshot */
            runner_include_screenshot?: boolean | null;
            /** Settle Delay Sec */
            settle_delay_sec?: number | null;
            /** Settle Mode */
            settle_mode?: ("strict" | "ratio" | "delay") | null;
            /** Settle Ocr Only */
            settle_ocr_only?: boolean | null;
            /** Settle Ratio Threshold */
            settle_ratio_threshold?: number | null;
            /** Settle Timeout */
            settle_timeout?: number | null;
            /** Temperature */
            temperature?: number | null;
            /** Vl Max Side */
            vl_max_side?: number | null;
        };
        /** ScheduleDetailData */
        ScheduleDetailData: {
            /** Active Schedule Run Id */
            active_schedule_run_id?: string | null;
            /** App Id */
            app_id: string;
            /** Artifact Path */
            artifact_path?: string | null;
            /** Assets Root */
            assets_root?: string | null;
            /** Created At */
            created_at: string;
            /** Cron Expr */
            cron_expr: string;
            /** Device Ref */
            device_ref: string;
            /** Enabled */
            enabled: boolean;
            /**
             * Fail Fast
             * @default false
             */
            fail_fast: boolean;
            /**
             * Headless
             * @default false
             */
            headless: boolean;
            /** Last Run At */
            last_run_at?: string | null;
            /** Latest Operation Id */
            latest_operation_id?: string | null;
            /** Name */
            name: string;
            /** Next Run At */
            next_run_at?: string | null;
            /** Plan Ids */
            plan_ids?: string[];
            /**
             * Queued Run Count
             * @default 0
             */
            queued_run_count: number;
            /** Recent Runs */
            recent_runs?: components["schemas"]["ScheduleRunSummaryData"][];
            /** Runtime Overrides */
            runtime_overrides?: {
                [key: string]: unknown;
            };
            /** Schedule Id */
            schedule_id: string;
            /** Timezone */
            timezone: string;
            /** Updated At */
            updated_at: string;
        };
        /** ScheduleListData */
        ScheduleListData: {
            /** Items */
            items?: components["schemas"]["ScheduleSummaryData"][];
            /**
             * Limit
             * @default 20
             */
            limit: number;
            /**
             * Offset
             * @default 0
             */
            offset: number;
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** ScheduleRunListData */
        ScheduleRunListData: {
            /** Items */
            items?: components["schemas"]["ScheduleRunSummaryData"][];
            /** Schedule Id */
            schedule_id: string;
        };
        /** ScheduleRunSummaryData */
        ScheduleRunSummaryData: {
            /** Created At */
            created_at: string;
            /** Error Code */
            error_code?: string | null;
            /** Error Message */
            error_message?: string | null;
            /** Finished At */
            finished_at?: string | null;
            /** Operation Id */
            operation_id?: string | null;
            /** Schedule Run Id */
            schedule_run_id: string;
            /** Scheduled For */
            scheduled_for: string;
            /** Started At */
            started_at?: string | null;
            /** Status */
            status: string;
            /** Triggered At */
            triggered_at?: string | null;
        };
        /** ScheduleSummaryData */
        ScheduleSummaryData: {
            /** App Id */
            app_id: string;
            /** Created At */
            created_at: string;
            /** Cron Expr */
            cron_expr: string;
            /** Device Ref */
            device_ref: string;
            /** Enabled */
            enabled: boolean;
            /** Last Run At */
            last_run_at?: string | null;
            /** Name */
            name: string;
            /** Next Run At */
            next_run_at?: string | null;
            /** Plan Ids */
            plan_ids?: string[];
            /** Schedule Id */
            schedule_id: string;
            /** Timezone */
            timezone: string;
            /** Updated At */
            updated_at: string;
        };
        /** ScheduleUpsertRequest */
        ScheduleUpsertRequest: {
            /** App Id */
            app_id: string;
            /** Artifact Path */
            artifact_path?: string | null;
            /** Assets Root */
            assets_root?: string | null;
            /** Cron Expr */
            cron_expr: string;
            /** Device Ref */
            device_ref: string;
            /**
             * Enabled
             * @default true
             */
            enabled: boolean;
            /**
             * Fail Fast
             * @default false
             */
            fail_fast: boolean;
            /**
             * Headless
             * @default false
             */
            headless: boolean;
            /** Name */
            name?: string | null;
            /** Plan Ids */
            plan_ids: string[];
            /** Runtime Overrides */
            runtime_overrides?: {
                [key: string]: string | number | boolean;
            };
            /** Timezone */
            timezone?: string | null;
        };
        /** ScreenKnowledgeCandidateDraft */
        ScreenKnowledgeCandidateDraft: {
            /** App Id */
            app_id: string;
            /** Card Id */
            card_id?: string | null;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            card_type: "screen";
            /** Confidence */
            confidence: number;
            payload: components["schemas"]["ScreenPayload"];
            source: components["schemas"]["KnowledgeSource"];
            /** Title */
            title: string;
        };
        /** ScreenKnowledgeCard */
        ScreenKnowledgeCard: {
            /** App Id */
            app_id: string;
            /** Card Id */
            card_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            card_type: "screen";
            /** Confidence */
            confidence: number;
            payload: components["schemas"]["ScreenPayload"];
            source: components["schemas"]["KnowledgeSource"];
            /**
             * Status
             * @enum {string}
             */
            status: "active" | "deprecated" | "archived";
            /** Title */
            title: string;
            /** Updated At */
            updated_at: string;
        };
        /** ScreenKnowledgeCardInput */
        ScreenKnowledgeCardInput: {
            /** App Id */
            app_id: string;
            /** Card Id */
            card_id?: string | null;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            card_type: "screen";
            /** Confidence */
            confidence: number;
            payload: components["schemas"]["ScreenPayload"];
            source: components["schemas"]["KnowledgeSource"];
            /**
             * Status
             * @default active
             * @enum {string}
             */
            status: "active" | "deprecated" | "archived";
            /** Title */
            title: string;
        };
        /** ScreenPayload */
        ScreenPayload: {
            /** Enter */
            enter?: string | null;
            /** Exit Signals */
            exit_signals?: string[];
            /** Key Elements */
            key_elements?: string[];
            /** Recognize */
            recognize?: string | null;
        };
        /** SettingsAgentsEditor */
        SettingsAgentsEditor: {
            analysis?: components["schemas"]["AgentConfigEditor"];
            judge?: components["schemas"]["AgentConfigEditor"];
            plan?: components["schemas"]["AgentConfigEditor"];
            review?: components["schemas"]["AgentConfigEditor"];
            runner?: components["schemas"]["AgentConfigEditor"];
        };
        /** SettingsConfigData */
        SettingsConfigData: {
            agents?: components["schemas"]["SettingsAgentsEditor"];
            /** Config Path */
            config_path: string;
            /**
             * File Exists
             * @default false
             */
            file_exists: boolean;
            gemini?: components["schemas"]["GeminiSectionEditor"];
            ios_bridge?: components["schemas"]["IOSBridgeConfigEditor"];
            openai_compatible?: components["schemas"]["OpenAICompatibleSectionEditor"];
            orchestration?: components["schemas"]["OrchestrationConfigEditor"];
            /** Provider */
            provider: string;
            proxy?: components["schemas"]["ProxyConfigEditor"];
            runtime?: components["schemas"]["RuntimeConfigEditor"];
            test_env?: components["schemas"]["TestEnvConfigEditor"];
        };
        /** SettingsConfigUpsertRequest */
        SettingsConfigUpsertRequest: {
            agents?: components["schemas"]["SettingsAgentsEditor"];
            gemini?: components["schemas"]["GeminiSectionEditor"];
            ios_bridge?: components["schemas"]["IOSBridgeConfigEditor"];
            openai_compatible?: components["schemas"]["OpenAICompatibleSectionEditor"];
            orchestration?: components["schemas"]["OrchestrationConfigEditor"];
            /**
             * Provider
             * @default openai_compatible
             * @enum {string}
             */
            provider: "openai_compatible" | "gemini";
            proxy?: components["schemas"]["ProxyConfigEditor"];
            runtime?: components["schemas"]["RuntimeConfigEditor"];
            test_env?: components["schemas"]["TestEnvConfigEditor"];
        };
        /** StepStartedEventPayload */
        StepStartedEventPayload: {
            /** Step */
            step: number;
        } & {
            [key: string]: unknown;
        };
        /** SuccessResponse[AppDetailData] */
        SuccessResponse_AppDetailData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["AppDetailData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[AppListData] */
        SuccessResponse_AppListData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["AppListData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[CancelOperationData] */
        SuccessResponse_CancelOperationData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["CancelOperationData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[CaseDeleteData] */
        SuccessResponse_CaseDeleteData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["CaseDeleteData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[CaseDetailData] */
        SuccessResponse_CaseDetailData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["CaseDetailData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[CaseRewritePreviewData] */
        SuccessResponse_CaseRewritePreviewData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["CaseRewritePreviewData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[CaseSearchData] */
        SuccessResponse_CaseSearchData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["CaseSearchData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[CloudAppsData] */
        SuccessResponse_CloudAppsData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["CloudAppsData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[CloudLinkData] */
        SuccessResponse_CloudLinkData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["CloudLinkData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[CloudLinksData] */
        SuccessResponse_CloudLinksData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["CloudLinksData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[CloudLoginStartData] */
        SuccessResponse_CloudLoginStartData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["CloudLoginStartData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[CloudSessionSummaryData] */
        SuccessResponse_CloudSessionSummaryData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["CloudSessionSummaryData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[CloudSyncPublishResultData] */
        SuccessResponse_CloudSyncPublishResultData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["CloudSyncPublishResultData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[CloudSyncPullResultData] */
        SuccessResponse_CloudSyncPullResultData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["CloudSyncPullResultData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[CloudSyncPushResultData] */
        SuccessResponse_CloudSyncPushResultData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["CloudSyncPushResultData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[CloudSyncStatusData] */
        SuccessResponse_CloudSyncStatusData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["CloudSyncStatusData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[CloudWorkspacesData] */
        SuccessResponse_CloudWorkspacesData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["CloudWorkspacesData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[DashboardSummaryData] */
        SuccessResponse_DashboardSummaryData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["DashboardSummaryData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[DeleteAppData] */
        SuccessResponse_DeleteAppData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["DeleteAppData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[DeviceInstallData] */
        SuccessResponse_DeviceInstallData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["DeviceInstallData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[DeviceListData] */
        SuccessResponse_DeviceListData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["DeviceListData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[DeviceStateData] */
        SuccessResponse_DeviceStateData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["DeviceStateData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[DeviceUnlockData] */
        SuccessResponse_DeviceUnlockData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["DeviceUnlockData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[InteractiveSessionAbortData] */
        SuccessResponse_InteractiveSessionAbortData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["InteractiveSessionAbortData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[InteractiveSessionCreateData] */
        SuccessResponse_InteractiveSessionCreateData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["InteractiveSessionCreateData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[InteractiveSessionFinalizeData] */
        SuccessResponse_InteractiveSessionFinalizeData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["InteractiveSessionFinalizeData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[InteractiveSessionGetData] */
        SuccessResponse_InteractiveSessionGetData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["InteractiveSessionGetData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[KnowledgeCandidateApproveData] */
        SuccessResponse_KnowledgeCandidateApproveData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["KnowledgeCandidateApproveData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[KnowledgeCandidateListData] */
        SuccessResponse_KnowledgeCandidateListData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["KnowledgeCandidateListData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[KnowledgeCandidateRejectData] */
        SuccessResponse_KnowledgeCandidateRejectData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["KnowledgeCandidateRejectData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[KnowledgeCardDeleteData] */
        SuccessResponse_KnowledgeCardDeleteData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["KnowledgeCardDeleteData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[KnowledgeCardGetData] */
        SuccessResponse_KnowledgeCardGetData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["KnowledgeCardGetData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[KnowledgeCardListData] */
        SuccessResponse_KnowledgeCardListData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["KnowledgeCardListData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[KnowledgeCardMutationData] */
        SuccessResponse_KnowledgeCardMutationData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["KnowledgeCardMutationData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[OperationArtifactsData] */
        SuccessResponse_OperationArtifactsData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["OperationArtifactsData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[OperationChildrenData] */
        SuccessResponse_OperationChildrenData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["OperationChildrenData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[OperationDetailData] */
        SuccessResponse_OperationDetailData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["OperationDetailData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[OperationEventsData] */
        SuccessResponse_OperationEventsData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["OperationEventsData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[OperationListData] */
        SuccessResponse_OperationListData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["OperationListData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[OperationSubmissionData] */
        SuccessResponse_OperationSubmissionData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["OperationSubmissionData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[PlanDetailData] */
        SuccessResponse_PlanDetailData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["PlanDetailData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[PlanImportData] */
        SuccessResponse_PlanImportData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["PlanImportData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[PlanListData] */
        SuccessResponse_PlanListData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["PlanListData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[RecordingAnalysisData] */
        SuccessResponse_RecordingAnalysisData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["RecordingAnalysisData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[RecordingBeginData] */
        SuccessResponse_RecordingBeginData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["RecordingBeginData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[RecordingCreateData] */
        SuccessResponse_RecordingCreateData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["RecordingCreateData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[RecordingExportData] */
        SuccessResponse_RecordingExportData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["RecordingExportData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[RecordingGetData] */
        SuccessResponse_RecordingGetData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["RecordingGetData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[RecordingInteractionData] */
        SuccessResponse_RecordingInteractionData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["RecordingInteractionData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[RecordingObservationData] */
        SuccessResponse_RecordingObservationData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["RecordingObservationData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[RecordingReplayData] */
        SuccessResponse_RecordingReplayData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["RecordingReplayData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[RecordingSessionData] */
        SuccessResponse_RecordingSessionData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["RecordingSessionData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[RecordingTapData] */
        SuccessResponse_RecordingTapData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["RecordingTapData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[RecordingTimelineData] */
        SuccessResponse_RecordingTimelineData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["RecordingTimelineData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[ReproduceOperationData] */
        SuccessResponse_ReproduceOperationData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["ReproduceOperationData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[RunArtifactChildrenData] */
        SuccessResponse_RunArtifactChildrenData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["RunArtifactChildrenData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[RunArtifactContentData] */
        SuccessResponse_RunArtifactContentData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["RunArtifactContentData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[ScheduleDetailData] */
        SuccessResponse_ScheduleDetailData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["ScheduleDetailData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[ScheduleListData] */
        SuccessResponse_ScheduleListData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["ScheduleListData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[ScheduleRunListData] */
        SuccessResponse_ScheduleRunListData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["ScheduleRunListData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[ScheduleSummaryData] */
        SuccessResponse_ScheduleSummaryData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["ScheduleSummaryData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[SettingsConfigData] */
        SuccessResponse_SettingsConfigData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["SettingsConfigData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** SuccessResponse[VerifyReadinessData] */
        SuccessResponse_VerifyReadinessData_: {
            /** Artifacts */
            artifacts?: {
                [key: string]: string;
            } | null;
            /** Command */
            command: string;
            data: components["schemas"]["VerifyReadinessData"];
            /**
             * Ok
             * @default true
             * @constant
             */
            ok: true;
        };
        /** TestCase */
        TestCase: {
            /** Acceptance Criteria Indices */
            acceptance_criteria_indices?: number[];
            ai_guidance?: components["schemas"]["AiGuidance"] | null;
            budget?: components["schemas"]["CaseBudget"] | null;
            /** Case Id */
            case_id: string;
            /** Expected */
            expected?: string[];
            /** Intent */
            intent: string;
            /**
             * Is Core Case
             * @default false
             */
            is_core_case: boolean;
            /** Post Action */
            post_action?: string[];
            /** Preconditions */
            preconditions?: string[];
            /** Procedure */
            procedure?: string[];
            /** Runner Goal */
            runner_goal: string;
            /** Setup */
            setup?: (components["schemas"]["HttpSetupStep"] | components["schemas"]["CommandSetupStep"])[];
            /** Source Metadata */
            source_metadata?: {
                [key: string]: string;
            };
            start_state?: components["schemas"]["CaseStartState"];
            /** Title */
            title: string;
        };
        /** TestCasePayload */
        TestCasePayload: {
            ai_guidance?: components["schemas"]["AiGuidance"] | null;
            budget?: components["schemas"]["CaseBudgetRequest"] | null;
            /** Case Id */
            case_id: string;
            /** Expected */
            expected?: string[];
            /** Intent */
            intent: string;
            /**
             * Is Core Case
             * @default false
             */
            is_core_case: boolean;
            /** Post Action */
            post_action?: string[];
            /** Preconditions */
            preconditions?: string[];
            /** Procedure */
            procedure?: string[];
            /** Runner Goal */
            runner_goal: string;
            /** Setup */
            setup?: (components["schemas"]["HttpSetupStep"] | components["schemas"]["CommandSetupStep"])[];
            /** Source Metadata */
            source_metadata?: {
                [key: string]: string;
            };
            start_state?: components["schemas"]["CaseStartStateRequest"];
            /** Title */
            title: string;
        };
        /** TestEnvConfigEditor */
        TestEnvConfigEditor: {
            /** Allowed Exec */
            allowed_exec?: string[];
            /** Bases */
            bases?: {
                [key: string]: components["schemas"]["HttpBaseConfigEditor"];
            };
        };
        /** TextInjectStepPayload */
        TextInjectStepPayload: {
            /**
             * Submit
             * @default false
             */
            submit: boolean;
            /** Text */
            text: string;
        };
        /** TimelineEntry */
        TimelineEntry: {
            /** After Observation Id */
            after_observation_id: string;
            /**
             * After Stabilized
             * @default true
             */
            after_stabilized: boolean;
            /** Before Observation Id */
            before_observation_id: string;
            /** Entry Id */
            entry_id: string;
            /** Forwarding Event Id */
            forwarding_event_id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "click" | "swipe" | "input" | "back";
            /** Recording Event Id */
            recording_event_id: string;
            /** Recording Id */
            recording_id: string;
            /** Seq */
            seq: number;
            /** Summary */
            summary?: string | null;
            /** Timestamp */
            timestamp?: string;
        };
        /** TokenUsage */
        TokenUsage: {
            /** Cached Input Tokens */
            cached_input_tokens?: number | null;
            /** Input Tokens */
            input_tokens?: number | null;
            /** Model */
            model?: string | null;
            /** Output Tokens */
            output_tokens?: number | null;
            /** Provider */
            provider?: string | null;
            /** Reasoning Tokens */
            reasoning_tokens?: number | null;
            /**
             * Request Count
             * @default 0
             */
            request_count: number;
            /** Total Tokens */
            total_tokens?: number | null;
        };
        /** TokenUsageData */
        TokenUsageData: {
            /** Cached Input Tokens */
            cached_input_tokens?: number | null;
            /** Input Tokens */
            input_tokens?: number | null;
            /** Model */
            model?: string | null;
            /** Output Tokens */
            output_tokens?: number | null;
            /** Provider */
            provider?: string | null;
            /** Reasoning Tokens */
            reasoning_tokens?: number | null;
            /**
             * Request Count
             * @default 0
             */
            request_count: number;
            /** Total Tokens */
            total_tokens?: number | null;
        };
        /** UpstreamReviewArtifacts */
        UpstreamReviewArtifacts: {
            /** Contract Version */
            contract_version?: string | null;
            /** Review Operation Id */
            review_operation_id?: string | null;
            /** Review Orchestration Path */
            review_orchestration_path?: string | null;
            /** Review Result Path */
            review_result_path?: string | null;
        };
        /** ValidationError */
        ValidationError: {
            /** Context */
            ctx?: Record<string, never>;
            /** Input */
            input?: unknown;
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
        };
        /** VerifyChangeCliRequest */
        VerifyChangeCliRequest: {
            /** Acceptance Criteria */
            acceptance_criteria?: string[];
            /** App Id */
            app_id: string;
            app_target?: components["schemas"]["AppTarget"] | null;
            /** Artifact Path */
            artifact_path?: string | null;
            /** Assets Root */
            assets_root?: string | null;
            /**
             * Auto Run
             * @default false
             */
            auto_run: boolean;
            /** Change Summary */
            change_summary?: string | null;
            /** Changed Files */
            changed_files?: string[];
            /** Device Ref */
            device_ref?: string | null;
            /** Diff Text */
            diff_text?: string | null;
            /**
             * Enable Plan Agent
             * @default false
             */
            enable_plan_agent: boolean;
            /**
             * Fail Fast
             * @default false
             */
            fail_fast: boolean;
            /** Provided Cases */
            provided_cases?: components["schemas"]["TestCase"][];
            /** Requirement Doc Path */
            requirement_doc_path?: string | null;
            /** Review Orchestration Path */
            review_orchestration_path?: string | null;
            /** Runtime Overrides */
            runtime_overrides?: {
                [key: string]: string | number | boolean;
            };
            /** Technical Doc Path */
            technical_doc_path?: string | null;
        };
        /** VerifyChangeOperationResultPayload */
        VerifyChangeOperationResultPayload: {
            /** App Id */
            app_id: string;
            /** Artifacts */
            artifacts: {
                [key: string]: string;
            };
            execution_result?: components["schemas"]["ExecutedPlanResult"] | null;
            /** Phase */
            phase: string;
            /** Plan Id */
            plan_id: string;
            plan_result: components["schemas"]["GeneratedPlanResult"];
        };
        /** VerifyReadinessData */
        VerifyReadinessData: {
            /** Api Key Configured */
            api_key_configured: boolean;
            /** Missing */
            missing?: string[];
            /** Model */
            model?: string | null;
            /** Provider */
            provider?: string | null;
            /** Ready */
            ready: boolean;
            /** Runner Configured */
            runner_configured: boolean;
            vision_preflight: components["schemas"]["VisionPreflightData"];
        };
        /** VisionPreflightData */
        VisionPreflightData: {
            /** Checked At */
            checked_at?: string | null;
            /** Message */
            message?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "not_run" | "cached_ok" | "ok" | "failed";
        };
        /** WebAppIdentity */
        WebAppIdentity: {
            /** Base Url */
            base_url?: string | null;
            /** Origin */
            origin?: string | null;
        };
        /** WorkflowAttemptFinishedEventPayload */
        WorkflowAttemptFinishedEventPayload: {
            /** Attempt Index */
            attempt_index?: number | null;
            /** Decision Type */
            decision_type?: string | null;
            /** Verdict */
            verdict?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** WorkflowAttemptStartedEventPayload */
        WorkflowAttemptStartedEventPayload: {
            /** Attempt Index */
            attempt_index?: number | null;
            /** Case Id */
            case_id?: string | null;
            /** Retry Count */
            retry_count?: number | null;
        } & {
            [key: string]: unknown;
        };
        /** WorkflowFinishedEventPayload */
        WorkflowFinishedEventPayload: {
            /** Attempt Count */
            attempt_count?: number | null;
            /** Decision Type */
            decision_type?: string | null;
            /** Verdict */
            verdict?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** WorkflowRetryScheduledEventPayload */
        WorkflowRetryScheduledEventPayload: {
            /** Attempt Index */
            attempt_index?: number | null;
            /** Focus Items */
            focus_items?: string[] | null;
            /** Handoff Summary */
            handoff_summary?: string | null;
            /** Reason */
            reason?: string | null;
            /** Retry Attempt */
            retry_attempt?: number | null;
            /** Retry Count */
            retry_count?: number | null;
            /** Retry Reason */
            retry_reason?: string | null;
            /** Supplemental Context */
            supplemental_context?: string[] | null;
        } & {
            [key: string]: unknown;
        };
        /** WorkflowStartedEventPayload */
        WorkflowStartedEventPayload: {
            /** Case Id */
            case_id?: string | null;
        } & {
            [key: string]: unknown;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    healthz_healthz_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: string;
                    };
                };
            };
        };
    };
    list_apps_v1_apps_get: {
        parameters: {
            query?: {
                platform?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_AppListData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_app_v1_apps_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AppUpsertRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_AppDetailData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_app_v1_apps__app_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                app_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_AppDetailData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    update_app_v1_apps__app_id__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                app_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AppUpsertRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_AppDetailData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    delete_app_v1_apps__app_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                app_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_DeleteAppData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_candidates_v1_apps__app_id__knowledge_candidates_get: {
        parameters: {
            query?: {
                status?: string | null;
                candidate_id?: string | null;
                limit?: number;
            };
            header?: never;
            path: {
                app_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_KnowledgeCandidateListData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    approve_candidate_v1_apps__app_id__knowledge_candidates__candidate_id__approve_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                app_id: string;
                candidate_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["KnowledgeCandidateDecisionRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_KnowledgeCandidateApproveData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    reject_candidate_v1_apps__app_id__knowledge_candidates__candidate_id__reject_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                app_id: string;
                candidate_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["KnowledgeCandidateDecisionRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_KnowledgeCandidateRejectData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_cards_v1_apps__app_id__knowledge_cards_get: {
        parameters: {
            query?: {
                q?: string | null;
                card_type?: ("screen" | "flow" | "assertion" | "issue" | "data" | "policy" | "domain_term") | null;
                status?: ("active" | "deprecated" | "archived") | null;
                limit?: number;
                offset?: number;
            };
            header?: never;
            path: {
                app_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_KnowledgeCardListData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_card_v1_apps__app_id__knowledge_cards_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                app_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["KnowledgeCardWriteRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_KnowledgeCardMutationData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_card_v1_apps__app_id__knowledge_cards__card_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                app_id: string;
                card_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_KnowledgeCardGetData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    update_card_v1_apps__app_id__knowledge_cards__card_id__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                app_id: string;
                card_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["KnowledgeCardWriteRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_KnowledgeCardMutationData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    delete_card_v1_apps__app_id__knowledge_cards__card_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                app_id: string;
                card_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_KnowledgeCardDeleteData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_cloud_apps_v1_cloud_apps_get: {
        parameters: {
            query: {
                workspace_id: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_CloudAppsData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    start_cloud_login_v1_cloud_auth_login_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_CloudLoginStartData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    logout_cloud_session_v1_cloud_auth_logout_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_CloudSessionSummaryData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_cloud_session_v1_cloud_auth_session_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_CloudSessionSummaryData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_cloud_workspaces_v1_cloud_auth_workspaces_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_CloudWorkspacesData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_cloud_links_v1_cloud_links_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_CloudLinksData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    put_cloud_link_v1_cloud_links_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CloudLinkUpsertRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_CloudLinkData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    put_cloud_link_active_v1_cloud_links_active_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CloudLinkActiveRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_CloudLinksData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    delete_cloud_link_v1_cloud_links__app_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                app_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_CloudLinksData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    post_cloud_sync_publish_v1_cloud_sync_publish_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CloudSyncPublishRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_CloudSyncPublishResultData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    post_cloud_sync_pull_v1_cloud_sync_pull_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["CloudSyncPullRequest"] | null;
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_CloudSyncPullResultData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    post_cloud_sync_push_v1_cloud_sync_push_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["CloudSyncPushRequest"] | null;
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_CloudSyncPushResultData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_cloud_sync_status_v1_cloud_sync_status_get: {
        parameters: {
            query?: {
                app_id?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_CloudSyncStatusData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unauthorized */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Forbidden */
            403: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    dashboard_summary_v1_dashboard_summary_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_DashboardSummaryData_"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_device_state_v1_device_state_get: {
        parameters: {
            query: {
                device_ref: string;
                platform?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_DeviceStateData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    unlock_device_v1_device_unlock_post: {
        parameters: {
            query: {
                device_ref: string;
                platform?: string | null;
                strategy?: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_DeviceUnlockData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_devices_v1_devices_get: {
        parameters: {
            query?: {
                platform?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_DeviceListData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    install_app_v1_devices_install_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DeviceInstallRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_DeviceInstallData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_interactive_session_v1_interactive_sessions_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateInteractiveSessionRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_InteractiveSessionCreateData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_interactive_session_v1_interactive_sessions__session_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_InteractiveSessionGetData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    abort_interactive_session_v1_interactive_sessions__session_id__abort_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_InteractiveSessionAbortData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    finalize_interactive_session_v1_interactive_sessions__session_id__finalize_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["FinalizeInteractiveSessionRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_InteractiveSessionFinalizeData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    plan_v1_plan_post: {
        parameters: {
            query?: {
                wait?: boolean;
                detach?: boolean;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PlanCliRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_OperationSubmissionData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_plans_v1_plans_get: {
        parameters: {
            query?: {
                app_id?: string | null;
                source?: string | null;
                case_count_mode?: string | null;
                limit?: number;
                offset?: number;
                include_latest_run?: boolean;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_PlanListData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    search_cases_v1_plans_cases_get: {
        parameters: {
            query?: {
                app_id?: string | null;
                plan_id?: string | null;
                case_id?: string | null;
                query?: string | null;
                is_core_case?: boolean | null;
                start_mode?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_CaseSearchData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_plan_v1_plans__app_id___plan_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                app_id: string;
                plan_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_PlanDetailData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    add_case_v1_plans__app_id___plan_id__cases_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                app_id: string;
                plan_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CaseUpsertRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_CaseDetailData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_case_v1_plans__app_id___plan_id__cases__case_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                app_id: string;
                plan_id: string;
                case_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_CaseDetailData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    update_case_v1_plans__app_id___plan_id__cases__case_id__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                app_id: string;
                plan_id: string;
                case_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CaseUpdateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_CaseDetailData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    delete_case_v1_plans__app_id___plan_id__cases__case_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                app_id: string;
                plan_id: string;
                case_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_CaseDeleteData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    replace_case_v1_plans__app_id___plan_id__cases__case_id__replace_put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                app_id: string;
                plan_id: string;
                case_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CaseUpsertRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_CaseDetailData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    rewrite_case_preview_v1_plans__app_id___plan_id__cases__case_id__rewrite_preview_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                app_id: string;
                plan_id: string;
                case_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CaseRewritePreviewRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_CaseRewritePreviewData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    reorder_cases_v1_plans__app_id___plan_id__cases_reorder_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                app_id: string;
                plan_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PlanCaseReorderRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_PlanDetailData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    import_plan_v1_plans_import_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PlanImportRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_PlanImportData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_recording_v1_recordings_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateRecordingRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_RecordingCreateData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_recording_v1_recordings__recording_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                recording_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_RecordingGetData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    analyze_recording_v1_recordings__recording_id__analysis_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                recording_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_RecordingAnalysisData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    submit_recording_analysis_v1_recordings__recording_id__analysis_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                recording_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_OperationSubmissionData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    begin_recording_v1_recordings__recording_id__begin_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                recording_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_RecordingBeginData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    cancel_recording_v1_recordings__recording_id__cancel_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                recording_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_RecordingSessionData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    record_interaction_v1_recordings__recording_id__events_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                recording_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RecordInteractionRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_RecordingInteractionData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    observe_tap_v1_recordings__recording_id__events_tap_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                recording_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ObserveTapRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_RecordingTapData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    export_recording_case_v1_recordings__recording_id__export_case_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                recording_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_RecordingExportData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_recording_observation_v1_recordings__recording_id__observations__observation_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                recording_id: string;
                observation_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_RecordingObservationData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    replay_recording_case_v1_recordings__recording_id__replay_case_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                recording_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_RecordingReplayData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    stop_recording_v1_recordings__recording_id__stop_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                recording_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_RecordingSessionData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_recording_timeline_v1_recordings__recording_id__timeline_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                recording_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_RecordingTimelineData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    review_v1_review_post: {
        parameters: {
            query?: {
                wait?: boolean;
                detach?: boolean;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReviewCliRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_OperationSubmissionData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    run_case_v1_run_case_post: {
        parameters: {
            query?: {
                wait?: boolean;
                detach?: boolean;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RunCaseCliRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_OperationSubmissionData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    run_plan_v1_run_plan_post: {
        parameters: {
            query?: {
                wait?: boolean;
                detach?: boolean;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RunPlanCliRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_OperationSubmissionData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    run_plans_v1_run_plans_post: {
        parameters: {
            query?: {
                wait?: boolean;
                detach?: boolean;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RunPlansCliRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_OperationSubmissionData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    runs_list_v1_runs_get: {
        parameters: {
            query?: {
                limit?: number;
                offset?: number;
                status?: ("queued" | "running" | "succeeded" | "failed" | "cancelled" | "interrupted") | null;
                kind?: ("plan" | "run_case" | "run_plan" | "run_plans" | "verify_change" | "review" | "optimize_case" | "knowledge_post_action" | "record_case" | "recording_analysis" | "interactive_session" | "app_install") | null;
                device_ref?: string | null;
                surface?: string | null;
                verification_verdict?: string | null;
                platform?: string | null;
                query?: string | null;
                run_type?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_OperationListData_"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    runs_get_v1_runs__operation_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                operation_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_OperationDetailData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    runs_artifacts_v1_runs__operation_id__artifacts_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                operation_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_OperationArtifactsData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    runs_artifact_children_v1_runs__operation_id__artifacts__artifact_id__children_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                operation_id: string;
                artifact_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_RunArtifactChildrenData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    runs_artifact_child_content_v1_runs__operation_id__artifacts__artifact_id__children__child_id__content_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                operation_id: string;
                artifact_id: string;
                child_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    runs_artifact_content_v1_runs__operation_id__artifacts__artifact_id__content_get: {
        parameters: {
            query?: {
                max_bytes?: number;
            };
            header?: never;
            path: {
                operation_id: string;
                artifact_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_RunArtifactContentData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    runs_artifact_download_v1_runs__operation_id__artifacts__artifact_id__download_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                operation_id: string;
                artifact_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    runs_cancel_v1_runs__operation_id__cancel_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                operation_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_CancelOperationData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    runs_children_v1_runs__operation_id__children_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                operation_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_OperationChildrenData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    runs_events_v1_runs__operation_id__events_get: {
        parameters: {
            query?: {
                after_seq?: number;
                limit?: number;
            };
            header?: never;
            path: {
                operation_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_OperationEventsData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    runs_reproduce_v1_runs__operation_id__reproduce_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                operation_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_ReproduceOperationData_"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_schedules_v1_schedules_get: {
        parameters: {
            query?: {
                enabled?: boolean | null;
                app_id?: string | null;
                keyword?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_ScheduleListData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_schedule_v1_schedules_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ScheduleUpsertRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_ScheduleDetailData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_schedule_v1_schedules__schedule_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                schedule_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_ScheduleDetailData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    update_schedule_v1_schedules__schedule_id__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                schedule_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ScheduleUpsertRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_ScheduleDetailData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    delete_schedule_v1_schedules__schedule_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                schedule_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_ScheduleSummaryData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_schedule_runs_v1_schedules__schedule_id__runs_get: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: never;
            path: {
                schedule_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_ScheduleRunListData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    disable_schedule_v1_schedules__schedule_id__disable_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                schedule_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_ScheduleSummaryData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    enable_schedule_v1_schedules__schedule_id__enable_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                schedule_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_ScheduleSummaryData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_settings_config_v1_settings_config_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_SettingsConfigData_"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    update_settings_config_v1_settings_config_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SettingsConfigUpsertRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_SettingsConfigData_"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    verify_change_v1_verify_change_post: {
        parameters: {
            query?: {
                wait?: boolean;
                detach?: boolean;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VerifyChangeCliRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_OperationSubmissionData_"];
                };
            };
            /** @description Bad Request */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    verify_readiness_v1_verify_readiness_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_VerifyReadinessData_"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    verify_readiness_probe_v1_verify_readiness_probe_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuccessResponse_VerifyReadinessData_"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
}

