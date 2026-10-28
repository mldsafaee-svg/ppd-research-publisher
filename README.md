# PPD Research Publisher

موتور اولیه شناسایی منابع و انتشار کنترل‌شده در کانال @PPD_Research_FA

## استقرار
1. GitHub → Settings → Secrets and variables → Actions → Secrets: secret با نام `TELEGRAM_BOT_TOKEN` ایجاد کنید.
2. همان بخش → Variables: متغیر `TELEGRAM_CHANNEL_ID` با مقدار `@PPD_Research_FA` ایجاد کنید (در نبود آن همین کانال مقدار پیش‌فرض است).
3. Settings → Actions → General → Workflow permissions را روی Read and write قرار دهید.
4. Actions → PPD research discovery and publishing → Run workflow → `test`.
5. در کانال پیام آزمایشی را بررسی کنید، سپس `discover` را اجرا کنید.

نکته: این نسخه فقط فراداده Crossref را شناسایی می‌کند. خواندن متن کامل، ترجمه و تحلیل خودکار، اتصال به Dropbox و Sheets هنوز اجرا نشده است. فقط رکورد دارای `status=approved` و خلاصه فارسی با لینک HTTPS منتشر می‌شود. مخزن عمومی است؛ هیچ توکنی در کد ثبت نکنید.
