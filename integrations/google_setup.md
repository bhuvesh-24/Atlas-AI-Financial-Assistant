# Google OAuth Setup (Gmail / Calendar / Drive / Sheets)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable APIs:
   - Gmail API
   - Google Calendar API
   - Google Drive API
   - Google Sheets API
3. Credentials → Create OAuth client ID → Application type **Web application**
4. Authorized redirect URIs: add your public callback, e.g.
   `https://your-app.up.railway.app/oauth/callback`
5. Copy Client ID + Client Secret into `.env`:
   ```
   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...
   GOOGLE_REDIRECT_URI=https://your-app.up.railway.app/oauth/callback
   ```
6. OAuth consent screen: add your email as test user while in testing mode.
7. Restart Atlas. In conversation say “Connect my Google account” — Atlas will send a one-time link.

Scopes requested (read-only where possible + calendar write for scheduling):
- gmail.readonly
- calendar.readonly + calendar.events
- drive.readonly
- spreadsheets.readonly
