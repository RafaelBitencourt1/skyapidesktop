from urllib.parse import quote

from .constants import BASE_URL
from .api_client import parse_kv_lines, _apply_kv

def build_request(endpoint_id, row):
    data = {}
    params = {}
    mailbox = quote(row.get("mailbox", ""), safe="@._+-")

    if endpoint_id == "app_feature_list":
        return "GET", f"{BASE_URL}/mailbox/{mailbox}/app-feature", params, data
    if endpoint_id == "app_feature_get":
        feature = quote(row.get("feature", ""), safe="._+-")
        return "GET", f"{BASE_URL}/mailbox/{mailbox}/app-feature/{feature}", params, data
    if endpoint_id == "app_feature_enable":
        feature = quote(row.get("feature", ""), safe="._+-")
        return "POST", f"{BASE_URL}/mailbox/{mailbox}/app-feature/{feature}", params, data
    if endpoint_id == "app_feature_disable":
        feature = quote(row.get("feature", ""), safe="._+-")
        return "DELETE", f"{BASE_URL}/mailbox/{mailbox}/app-feature/{feature}", params, data
    if endpoint_id == "mailbox_list":
        if row.get("query"):
            params["query"] = row.get("query")
        return "GET", f"{BASE_URL}/mailbox", params, data
    if endpoint_id == "mailbox_get":
        return "GET", f"{BASE_URL}/mailbox/{mailbox}", params, data
    if endpoint_id == "mailbox_create":
        data = {
            "mail": row.get("mail", ""),
            "displayname": row.get("displayname", ""),
            "password": row.get("password", ""),
            "accounttype": row.get("accounttype", ""),
        }
        return "POST", f"{BASE_URL}/mailbox", params, data
    if endpoint_id == "mailbox_update_password":
        data = {
            "password": row.get("password", ""),
            "forcepasswordchange": row.get("forcepasswordchange", "false"),
        }
        return "PUT", f"{BASE_URL}/mailbox/{mailbox}", params, data
    if endpoint_id == "mailbox_update_status":
        data = {"accountstatus": row.get("accountstatus", "")}
        return "PUT", f"{BASE_URL}/mailbox/{mailbox}", params, data
    if endpoint_id == "mailbox_update_title":
        data = {"title": row.get("title", "")}
        return "PUT", f"{BASE_URL}/mailbox/{mailbox}", params, data
    if endpoint_id == "mailbox_add_alias":
        alias = row.get("alias", "")
        data = {f"mailalternateaddress[{alias}]": "true"}
        return "PUT", f"{BASE_URL}/mailbox/{mailbox}", params, data
    if endpoint_id == "mailbox_remove_alias":
        alias = row.get("alias", "")
        data = {f"mailalternateaddress[{alias}]": ""}
        return "PUT", f"{BASE_URL}/mailbox/{mailbox}", params, data
    if endpoint_id == "mailbox_update_product":
        data = {
            "accounttype": row.get("accounttype", ""),
            "confirm_purchase": row.get("confirm_purchase", "true"),
        }
        return "PUT", f"{BASE_URL}/mailbox/{mailbox}", params, data
    if endpoint_id == "mailbox_update_generic":
        data = parse_kv_lines(row.get("data_kv", ""))
        for key, value in row.items():
            if key in ("mailbox", "data_kv"):
                continue
            if value:
                data[key] = value
        return "PUT", f"{BASE_URL}/mailbox/{mailbox}", params, data
    if endpoint_id == "mailbox_rename":
        data = {"mail": row.get("novo_mail", "")}
        return "PUT", f"{BASE_URL}/mailbox/{mailbox}/rename", params, data
    if endpoint_id == "mailbox_delete":
        return "DELETE", f"{BASE_URL}/mailbox/{mailbox}", params, data
    if endpoint_id == "mailbox_remove_all_aliases":
        return "DELETE", f"{BASE_URL}/mailbox/{mailbox}/mailalternateaddress", params, data
    if endpoint_id == "custom_field_list":
        return "GET", f"{BASE_URL}/mailbox/{mailbox}/custom-field", params, data
    if endpoint_id == "custom_field_create":
        data = {"name": row.get("name", ""), "value": row.get("value", "")}
        return "POST", f"{BASE_URL}/mailbox/{mailbox}/custom-field", params, data
    if endpoint_id == "custom_field_update":
        field_name = quote(row.get("field_name", ""), safe="._+-")
        data = {"value": row.get("value", "")}
        return "PUT", f"{BASE_URL}/mailbox/{mailbox}/custom-field/{field_name}", params, data
    if endpoint_id == "custom_field_delete":
        field_name = quote(row.get("field_name", ""), safe="._+-")
        return "DELETE", f"{BASE_URL}/mailbox/{mailbox}/custom-field/{field_name}", params, data
    if endpoint_id == "deleted_list":
        if row.get("filters_email"):
            params["filters[email]"] = row.get("filters_email")
        return "GET", f"{BASE_URL}/mailbox/deleted", params, data
    if endpoint_id == "deleted_get":
        return "GET", f"{BASE_URL}/mailbox/deleted/{mailbox}", params, data
    if endpoint_id == "deleted_restore":
        return "PUT", f"{BASE_URL}/mailbox/deleted/{mailbox}/restore", params, data
    if endpoint_id == "deleted_remove":
        return "DELETE", f"{BASE_URL}/mailbox/deleted/{mailbox}", params, data

    # ── Caixas Postais - Retencao e Bloqueio ────────────────
    if endpoint_id == "mailbox_batch_retention":
        folder = row.get("rule_folder", "inbox")
        policy = row.get("rule_policy", "1")
        days_val = row.get("rule_days", "30")
        try:
            policy = int(policy)
        except (ValueError, TypeError):
            policy = 1
        try:
            days_val = int(days_val)
        except (ValueError, TypeError):
            days_val = 30
        json_payload = {
            "data": [
                {
                    "email": mailbox,
                    "rule": [{"folder": folder, "policy": policy, "days": days_val}],
                }
            ]
        }
        return "POST", f"{BASE_URL}/mailbox/retention", params, {"__json__": json_payload}
    if endpoint_id == "mailbox_block_period_get":
        return "GET", f"{BASE_URL}/mailbox/{mailbox}/blockperiod", params, data
    if endpoint_id == "mailbox_block_period_create":
        return "POST", f"{BASE_URL}/mailbox/{mailbox}/blockperiod", params, data
    if endpoint_id == "mailbox_block_period_delete":
        return "DELETE", f"{BASE_URL}/mailbox/{mailbox}/blockperiod", params, data

    # ── Restaurar mensagens ─────────────────────────────────
    if endpoint_id == "mailbox_backup_list":
        for k in ("page", "perPage", "dateFrom", "dateTo"):
            if row.get(k):
                params[k] = row[k]
        return "GET", f"{BASE_URL}/mailbox/{mailbox}/backup", params, data
    if endpoint_id == "mailbox_backup_folders":
        backup_id = row.get("backup_id", "")
        return "GET", f"{BASE_URL}/mailbox/{mailbox}/backup/{backup_id}/folders", params, data
    if endpoint_id == "mailbox_backup_restore":
        backup_id = row.get("backup_id", "")
        json_payload = {}
        if row.get("restoreFolders"):
            json_payload["restoreFolders"] = [f.strip() for f in row["restoreFolders"].split(",")]
        if row.get("restoreDestination"):
            json_payload["restoreDestination"] = row["restoreDestination"]
        return "POST", f"{BASE_URL}/mailbox/{mailbox}/backup/{backup_id}/restore", params, {"__json__": json_payload}
    if endpoint_id == "mailbox_backup_history":
        for k in ("page", "perPage", "status"):
            if row.get(k):
                params[k] = row[k]
        return "GET", f"{BASE_URL}/mailbox/{mailbox}/backup/history", params, data

    # ── Dominios ───────────────────────────────────────────
    domain = quote(row.get("domain", ""), safe="._-")
    if endpoint_id == "domain_list":
        if row.get("query"):
            params["query"] = row["query"]
        return "GET", f"{BASE_URL}/domain", params, data
    if endpoint_id == "domain_get":
        return "GET", f"{BASE_URL}/domain/{domain}", params, data
    if endpoint_id == "domain_create":
        data["name"] = row.get("domain", "")
        return "POST", f"{BASE_URL}/domain", params, data
    if endpoint_id == "domain_update":
        for k in ("forcepasswordchange", "status"):
            if row.get(k):
                data[k] = row[k]
        _apply_kv(data, row.get("data_kv", ""))
        return "PUT", f"{BASE_URL}/domain/{domain}", params, data
    if endpoint_id == "domain_delete":
        return "DELETE", f"{BASE_URL}/domain/{domain}", params, data
    if endpoint_id == "domain_mail_products":
        return "GET", f"{BASE_URL}/domain/{domain}/product", params, data
    if endpoint_id == "domain_app_feature_list":
        return "GET", f"{BASE_URL}/domain/{domain}/appfeature", params, data
    feature = quote(row.get("feature", ""), safe="._-")
    if endpoint_id == "domain_app_feature_get":
        return "GET", f"{BASE_URL}/domain/{domain}/appfeature/{feature}", params, data
    if endpoint_id == "domain_app_feature_enable":
        return "POST", f"{BASE_URL}/domain/{domain}/appfeature/{feature}", params, data
    if endpoint_id == "domain_app_feature_disable":
        return "DELETE", f"{BASE_URL}/domain/{domain}/appfeature/{feature}", params, data
    client_id = row.get("client_id", "")
    if endpoint_id == "domain_property_add":
        data["clientId"] = client_id
        return "POST", f"{BASE_URL}/domain/{domain}/property", params, data
    if endpoint_id == "domain_property_check":
        params["clientId"] = client_id
        return "GET", f"{BASE_URL}/domain/{domain}/property", params, data

    # ── Grupos de e-mail ───────────────────────────────────
    group_mail = quote(row.get("group_mail", ""), safe="._-@")
    if endpoint_id == "group_list":
        if row.get("query"):
            params["query"] = row["query"]
        return "GET", f"{BASE_URL}/group", params, data
    if endpoint_id == "group_get":
        return "GET", f"{BASE_URL}/group/{group_mail}", params, data
    if endpoint_id == "group_create":
        data["email"] = row.get("group_mail", "")
        data["displayname"] = row.get("displayname", "")
        return "POST", f"{BASE_URL}/group", params, data
    if endpoint_id == "group_update":
        _apply_kv(data, row.get("data_kv", ""))
        return "PUT", f"{BASE_URL}/group/{group_mail}", params, data
    if endpoint_id == "group_delete":
        return "DELETE", f"{BASE_URL}/group/{group_mail}", params, data

    # ── Clientes ──────────────────────────────────────────
    client_id2 = row.get("client_id", "")
    product_id = row.get("product_id", "")
    if endpoint_id == "client_list":
        for k in ("query", "page", "perPage"):
            if row.get(k):
                params[k] = row[k]
        return "GET", f"{BASE_URL}/client", params, data
    if endpoint_id == "client_get":
        return "GET", f"{BASE_URL}/client/{client_id2}", params, data
    if endpoint_id == "client_create":
        data["name"] = row.get("client_name", "")
        data["taxNumber"] = row.get("taxNumber", "")
        data["parentId"] = row.get("parentId", "")
        return "POST", f"{BASE_URL}/client", params, data
    if endpoint_id == "client_block":
        if row.get("reason"):
            data["reason"] = row["reason"]
        return "PUT", f"{BASE_URL}/client/{client_id2}/block", params, data
    if endpoint_id == "client_unblock":
        return "PUT", f"{BASE_URL}/client/{client_id2}/unblock", params, data
    if endpoint_id == "client_product_list":
        return "GET", f"{BASE_URL}/client/{client_id2}/product", params, data
    if endpoint_id == "client_product_get":
        return "GET", f"{BASE_URL}/client/{client_id2}/product/{product_id}", params, data
    if endpoint_id == "client_product_create":
        data["product"] = row.get("product", "")
        data["amount"] = row.get("amount", "")
        return "POST", f"{BASE_URL}/client/{client_id2}/product", params, data
    if endpoint_id == "client_product_update":
        data["amount"] = row.get("amount", "")
        return "PUT", f"{BASE_URL}/client/{client_id2}/product/{product_id}", params, data
    if endpoint_id == "client_product_delete":
        return "DELETE", f"{BASE_URL}/client/{client_id2}/product/{product_id}", params, data
    if endpoint_id == "client_app_feature_list":
        return "GET", f"{BASE_URL}/client/{client_id2}/appfeature", params, data
    feature2 = quote(row.get("feature", ""), safe="._-")
    if endpoint_id == "client_app_feature_get":
        return "GET", f"{BASE_URL}/client/{client_id2}/appfeature/{feature2}", params, data
    if endpoint_id == "client_app_feature_enable":
        return "POST", f"{BASE_URL}/client/{client_id2}/appfeature/{feature2}", params, data
    if endpoint_id == "client_app_feature_disable":
        return "DELETE", f"{BASE_URL}/client/{client_id2}/appfeature/{feature2}", params, data
    if endpoint_id == "client_custom_field_list":
        return "GET", f"{BASE_URL}/client/{client_id2}/customfield", params, data
    if endpoint_id == "client_custom_field_create":
        data["name"] = row.get("name", "")
        data["label"] = row.get("cf_label", "")
        data["type"] = row.get("cf_type", "")
        return "POST", f"{BASE_URL}/client/{client_id2}/customfield", params, data
    field_name = row.get("field_name", "")
    if endpoint_id == "client_custom_field_update":
        data["label"] = row.get("cf_label", "")
        data["type"] = row.get("cf_type", "")
        return "PUT", f"{BASE_URL}/client/{client_id2}/customfield/{field_name}", params, data
    if endpoint_id == "client_custom_field_delete":
        return "DELETE", f"{BASE_URL}/client/{client_id2}/customfield/{field_name}", params, data
    webhook_id = row.get("webhook_id", "")
    if endpoint_id == "client_webhook_list":
        if row.get("filters_httpMethod"):
            params["filters[httpMethod]"] = row["filters_httpMethod"]
        return "GET", f"{BASE_URL}/client/{client_id2}/webhook", params, data
    if endpoint_id == "client_webhook_get":
        return "GET", f"{BASE_URL}/client/{client_id2}/webhook/{webhook_id}", params, data
    if endpoint_id == "client_webhook_responses":
        return "GET", f"{BASE_URL}/client/{client_id2}/webhook/{webhook_id}/responses", params, data
    if endpoint_id == "client_webhook_create":
        data["url"] = row.get("url", "")
        data["httpMethod"] = row.get("httpMethod", "")
        data["webHook"] = row.get("webHook", "")
        return "POST", f"{BASE_URL}/client/{client_id2}/webhook", params, data
    if endpoint_id == "client_webhook_update":
        data["url"] = row.get("url", "")
        data["httpMethod"] = row.get("httpMethod", "")
        data["webHook"] = row.get("webHook", "")
        return "PUT", f"{BASE_URL}/client/{client_id2}/webhook/{webhook_id}", params, data
    if endpoint_id == "client_webhook_delete":
        return "DELETE", f"{BASE_URL}/client/{client_id2}/webhook/{webhook_id}", params, data

    # ── Hospedagem ─────────────────────────────────────────
    site = quote(row.get("site", ""), safe="._-")
    if endpoint_id == "hosting_list":
        if row.get("filter_name"):
            params["filter[name]"] = row["filter_name"]
        return "GET", f"{BASE_URL}/hosting", params, data
    if endpoint_id == "hosting_get":
        return "GET", f"{BASE_URL}/hosting/{site}", params, data
    if endpoint_id == "hosting_update_status":
        data["active"] = row.get("active", "false")
        return "PUT", f"{BASE_URL}/hosting/{site}/status", params, data
    if endpoint_id == "hosting_create":
        for k in ("name", "operationSystem", "clientId", "productId", "ftpLoginId", "password", "paymentInfoId", "confirmPurchase"):
            pass
        data["name"] = row.get("site_name", "")
        data["operationSystem"] = row.get("operation_system", "linux")
        data["clientId"] = row.get("client_id", "")
        data["productId"] = row.get("product_id", "")
        data["ftpLoginId"] = row.get("ftp_login_id", "")
        data["password"] = row.get("password", "")
        if row.get("payment_info_id"):
            data["paymentInfoId"] = row["payment_info_id"]
        if row.get("confirm_purchase"):
            data["confirmPurchase"] = row["confirm_purchase"]
        return "POST", f"{BASE_URL}/hosting/{site}", params, data
    if endpoint_id == "hosting_delete":
        return "DELETE", f"{BASE_URL}/hosting/{site}", params, data
    alias_name = quote(row.get("alias_name", ""), safe="._-")
    if endpoint_id == "hosting_alias_list":
        return "GET", f"{BASE_URL}/hosting/{site}/alias", params, data
    if endpoint_id == "hosting_alias_get":
        return "GET", f"{BASE_URL}/hosting/{site}/alias/{alias_name}", params, data
    if endpoint_id == "hosting_alias_update":
        if row.get("seo_redirect"):
            data["seoRedirect"] = row["seo_redirect"]
        if row.get("alias_new_name"):
            data["name"] = row["alias_new_name"]
        return "PUT", f"{BASE_URL}/hosting/{site}/alias/{alias_name}", params, data
    if endpoint_id == "hosting_alias_create":
        data["name"] = row.get("alias_new_name", "")
        if row.get("seo_redirect"):
            data["seoRedirect"] = row["seo_redirect"]
        return "POST", f"{BASE_URL}/hosting/{site}/alias", params, data
    if endpoint_id == "hosting_alias_delete":
        return "DELETE", f"{BASE_URL}/hosting/{site}/alias/{alias_name}", params, data
    ftp_login = quote(row.get("ftp_login", ""), safe="._-")
    if endpoint_id == "hosting_ftp_list":
        return "GET", f"{BASE_URL}/hosting/{site}/ftp", params, data
    if endpoint_id == "hosting_ftp_create":
        data["login"] = row.get("login", "")
        data["password"] = row.get("password", "")
        if row.get("root_path"):
            data["rootPath"] = row["root_path"]
        if row.get("create_dir"):
            data["createDir"] = row["create_dir"]
        return "POST", f"{BASE_URL}/hosting/{site}/ftp", params, data
    if endpoint_id == "hosting_ftp_update":
        data["password"] = row.get("password", "")
        return "PUT", f"{BASE_URL}/hosting/{site}/ftp/{ftp_login}", params, data
    if endpoint_id == "hosting_ftp_delete":
        return "DELETE", f"{BASE_URL}/hosting/{site}/ftp/{ftp_login}", params, data
    db_name = quote(row.get("db_name", ""), safe="._-")
    db_login = quote(row.get("db_login", ""), safe="._-")
    if endpoint_id == "hosting_db_list":
        return "GET", f"{BASE_URL}/hosting/{site}/database", params, data
    if endpoint_id == "hosting_db_get":
        return "GET", f"{BASE_URL}/hosting/{site}/database/{db_name}", params, data
    if endpoint_id == "hosting_db_create":
        data["name"] = row.get("db_name_new", "")
        return "POST", f"{BASE_URL}/hosting/{site}/database", params, data
    if endpoint_id == "hosting_db_delete":
        return "DELETE", f"{BASE_URL}/hosting/{site}/database/{db_name}", params, data
    if endpoint_id == "hosting_db_user_list":
        return "GET", f"{BASE_URL}/hosting/{site}/database/{db_name}/user", params, data
    if endpoint_id == "hosting_db_user_get":
        return "GET", f"{BASE_URL}/hosting/{site}/database/{db_name}/user/{db_login}", params, data
    if endpoint_id == "hosting_db_user_create":
        data["login"] = row.get("login", "")
        data["password"] = row.get("password", "")
        return "POST", f"{BASE_URL}/hosting/{site}/database/{db_name}/user", params, data
    if endpoint_id == "hosting_db_user_update":
        data["login"] = row.get("login", "")
        data["password"] = row.get("password", "")
        return "PUT", f"{BASE_URL}/hosting/{site}/database/user/{db_login}", params, data
    if endpoint_id == "hosting_db_user_delete":
        return "DELETE", f"{BASE_URL}/hosting/{site}/database/{db_name}/user/{db_login}", params, data
    if endpoint_id == "hosting_php_versions":
        return "GET", f"{BASE_URL}/hosting/{site}/php/versions", params, data
    if endpoint_id == "hosting_php_info":
        return "GET", f"{BASE_URL}/hosting/{site}/php", params, data
    if endpoint_id == "hosting_php_update":
        _apply_kv(data, row.get("data_kv", ""))
        return "PUT", f"{BASE_URL}/hosting/{site}/php", params, data

    # ── Dashboard ──────────────────────────────────────────
    if endpoint_id == "dashboard_get":
        return "GET", f"{BASE_URL}/dashboard", params, data

    # ── Template ──────────────────────────────────────────
    if endpoint_id == "template_list":
        return "GET", f"{BASE_URL}/template", params, data

    # ── Usuarios Administrativos ───────────────────────────
    username = quote(row.get("username", ""), safe="._-")
    if endpoint_id == "useradmin_create":
        data["username"] = row.get("username", "")
        data["email"] = row.get("email", "")
        data["password"] = row.get("password", "")
        return "POST", f"{BASE_URL}/useradmin", params, data
    if endpoint_id == "useradmin_change_password":
        data["password"] = row.get("password", "")
        data["actual"] = row.get("actual", "")
        return "PUT", f"{BASE_URL}/useradmin/{username}/password", params, data
    if endpoint_id == "useradmin_2fa_config":
        return "GET", f"{BASE_URL}/useradmin/{username}/2fa", params, data
    if endpoint_id == "useradmin_2fa_enable":
        data["secret"] = row.get("secret", "")
        data["code"] = row.get("code", "")
        return "POST", f"{BASE_URL}/useradmin/{username}/2fa", params, data
    if endpoint_id == "useradmin_2fa_disable":
        return "DELETE", f"{BASE_URL}/useradmin/{username}/2fa", params, data
    if endpoint_id == "useradmin_2fa_mandatory_on":
        return "POST", f"{BASE_URL}/useradmin/{username}/2fa/mandatory", params, data
    if endpoint_id == "useradmin_2fa_mandatory_off":
        return "DELETE", f"{BASE_URL}/useradmin/{username}/2fa/mandatory", params, data

    # ── WebHooks globais ──────────────────────────────────
    if endpoint_id == "webhook_list":
        return "GET", f"{BASE_URL}/webhook", params, data

    # ── Backup ────────────────────────────────────────────
    bk_id = row.get("backup_client_id", "")
    bs_id = row.get("backup_set_id", "")
    bj_id = row.get("backup_job_id", "")
    if endpoint_id == "backup_client_list":
        for k in ("clientId", "search", "days"):
            if row.get(k):
                params[k] = row[k]
        return "GET", f"{BASE_URL}/backup", params, data
    if endpoint_id == "backup_client_get":
        return "GET", f"{BASE_URL}/backup/{bk_id}", params, data
    if endpoint_id == "backup_client_create":
        data["clientId"] = row.get("clientId", "")
        data["backupServerId"] = row.get("backupServerId", "")
        data["backupClientId"] = row.get("backupClientId", "")
        data["password"] = row.get("password", "")
        if row.get("timezone"):
            data["timezone"] = row["timezone"]
        if row.get("language"):
            data["language"] = row["language"]
        return "POST", f"{BASE_URL}/backup", params, data
    if endpoint_id == "backup_client_update":
        for k in ("timezone", "language"):
            if row.get(k):
                data[k] = row[k]
        _apply_kv(data, row.get("data_kv", ""))
        return "PUT", f"{BASE_URL}/backup/{bk_id}", params, data
    if endpoint_id == "backup_client_update_status":
        data["status"] = row.get("status", "")
        return "PUT", f"{BASE_URL}/backup/{bk_id}/status", params, data
    if endpoint_id == "backup_client_update_password":
        data["password"] = row.get("password", "")
        return "PUT", f"{BASE_URL}/backup/{bk_id}/password", params, data
    if endpoint_id == "backup_client_delete":
        return "DELETE", f"{BASE_URL}/backup/{bk_id}", params, data
    if endpoint_id == "backup_routine_list":
        return "GET", f"{BASE_URL}/backup/{bk_id}/set", params, data
    if endpoint_id == "backup_routine_get":
        return "GET", f"{BASE_URL}/backup/{bk_id}/set/{bs_id}", params, data
    if endpoint_id == "backup_history_list":
        return "GET", f"{BASE_URL}/backup/{bk_id}/set/{bs_id}/job", params, data
    if endpoint_id == "backup_history_get":
        return "GET", f"{BASE_URL}/backup/{bk_id}/set/{bs_id}/job/{bj_id}", params, data

    # ── Envios SMTP ────────────────────────────────────────
    smtp_cid = row.get("smtp_client_id", "")
    if endpoint_id == "smtp_report_summary":
        params["dateFrom"] = row.get("dateFrom", "")
        params["dateTo"] = row.get("dateTo", "")
        for k in ("clientId", "status"):
            if row.get(k):
                params[k] = row[k]
        return "GET", f"{BASE_URL}/smtp/report/summary", params, data
    if endpoint_id == "smtp_delivery_list":
        for k in ("mailbox", "status", "dateFrom", "dateTo", "page", "perPage"):
            if row.get(k):
                params[k] = row[k]
        return "GET", f"{BASE_URL}/smtp/{smtp_cid}/delivery", params, data
    if endpoint_id == "smtp_delivery_get":
        delivery_id = row.get("delivery_id", "")
        return "GET", f"{BASE_URL}/smtp/{smtp_cid}/delivery/{delivery_id}", params, data
    if endpoint_id == "smtp_report_details":
        params["dateFrom"] = row.get("dateFrom", "")
        params["dateTo"] = row.get("dateTo", "")
        for k in ("clientId", "status"):
            if row.get(k):
                params[k] = row[k]
        return "GET", f"{BASE_URL}/smtp/report", params, data
    if endpoint_id == "smtp_report_count":
        params["dateFrom"] = row.get("dateFrom", "")
        params["dateTo"] = row.get("dateTo", "")
        if row.get("status"):
            params["status"] = row["status"]
        return "GET", f"{BASE_URL}/smtp/report/count", params, data
    if endpoint_id == "smtp_report_send_csv":
        data["dateFrom"] = row.get("dateFrom", "")
        data["dateTo"] = row.get("dateTo", "")
        if row.get("status"):
            data["status"] = row["status"]
        return "POST", f"{BASE_URL}/smtp/report/csv", params, data
    if endpoint_id == "smtp_product_list":
        return "GET", f"{BASE_URL}/smtp/product", params, data
    if endpoint_id == "smtp_product_get":
        return "GET", f"{BASE_URL}/smtp/{smtp_cid}/product", params, data
    if endpoint_id == "smtp_product_update":
        _apply_kv(data, row.get("data_kv", ""))
        return "POST", f"{BASE_URL}/smtp/{smtp_cid}/product", params, data
    if endpoint_id == "smtp_message_send":
        _apply_kv(data, row.get("data_kv", ""))
        return "POST", f"{BASE_URL}/smtp/message", params, data
    if endpoint_id == "smtp_message_status":
        message_id = row.get("message_id", "")
        return "GET", f"{BASE_URL}/smtp/message/{message_id}", params, data

    # ── Registro de Dominio ───────────────────────────────
    provider = quote(row.get("provider", ""), safe="")
    reg_domain = quote(row.get("domain", ""), safe="._-")
    if endpoint_id == "domain_reg_check":
        return "GET", f"{BASE_URL}/domainreg/{provider}/domain/{reg_domain}/check", params, data
    if endpoint_id == "domain_reg_get":
        params["clientId"] = row.get("clientId", "")
        return "GET", f"{BASE_URL}/domainreg/{provider}/domain/{reg_domain}", params, data
    if endpoint_id == "domain_reg_list":
        params["clientId"] = row.get("clientId", "")
        return "GET", f"{BASE_URL}/domainreg/{provider}/domain", params, data
    if endpoint_id == "domain_reg_autorenew":
        return "PUT", f"{BASE_URL}/domainreg/{provider}/domain/{reg_domain}/autorenew", params, data
    if endpoint_id == "domain_reg_create":
        _apply_kv(data, row.get("data_kv", ""))
        return "POST", f"{BASE_URL}/domainreg/{provider}/domain", params, data
    if endpoint_id == "domain_reg_ns_list":
        return "GET", f"{BASE_URL}/domainreg/{provider}/domain/{reg_domain}/nameserver", params, data
    if endpoint_id == "domain_reg_ns_update":
        _apply_kv(data, row.get("data_kv", ""))
        return "PATCH", f"{BASE_URL}/domainreg/{provider}/domain/{reg_domain}/nameserver", params, data
    if endpoint_id == "domain_reg_org_check":
        document = quote(row.get("document", ""), safe="")
        return "GET", f"{BASE_URL}/domainreg/{provider}/organization/{document}", params, data

    raise ValueError("Endpoint invalido")


def build_dns_request(endpoint_id, row):
    params = {}
    data = {}
    domain = quote(row.get("domain", ""), safe="._-")

    if endpoint_id == "dns_get":
        return "GET", f"{BASE_URL}/dns/{domain}", params, data
    if endpoint_id == "dns_entry_list":
        if row.get("filters_name"):
            params["filters[name]"] = row.get("filters_name")
        field = row.get("order_by_field", "").strip()
        direction = (row.get("order_by_dir", "ASC") or "ASC").strip().upper()
        if field:
            params[f"order_by[{field}]"] = direction
        return "GET", f"{BASE_URL}/dns/{domain}/entry", params, data
    if endpoint_id == "dns_entry_get":
        entry_id = row.get("entry_id", "")
        return "GET", f"{BASE_URL}/dns/{domain}/entry/{entry_id}", params, data
    if endpoint_id == "dns_zone_list":
        if row.get("filters_name"):
            params["filters[name]"] = row.get("filters_name")
        return "GET", f"{BASE_URL}/dns", params, data
    if endpoint_id == "dns_zone_create":
        data["name"] = row.get("domain", "")
        return "POST", f"{BASE_URL}/dns", params, data
    if endpoint_id == "dns_zone_delete":
        return "DELETE", f"{BASE_URL}/dns/{domain}", params, data
    if endpoint_id == "dns_entry_create":
        data["name"] = row.get("dns_name", "")
        data["type"] = row.get("dns_type", "")
        data["value"] = row.get("dns_value", "")
        if row.get("dns_ttl"):
            data["ttl"] = row.get("dns_ttl")
        return "POST", f"{BASE_URL}/dns/{domain}/entry", params, data
    if endpoint_id == "dns_entry_delete":
        entry_id = row.get("entry_id", "")
        return "DELETE", f"{BASE_URL}/dns/{domain}/entry/{entry_id}", params, data
    raise ValueError("Endpoint DNS invalido")


