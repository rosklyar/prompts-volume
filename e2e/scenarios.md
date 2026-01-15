# E2E Verification Scenarios

Run these scenarios using Playwright MCP tools after docker-compose and frontend are up.

## Required: Login Flow
1. Navigate to http://localhost:5173
2. Fill email: admin@example.com, password: changethis
3. Click "Log in"
4. Verify: redirected to dashboard, see "$10.00" balance

## Optional: Add scenarios relevant to your change

### Search and Add Prompt to Group
1. Login as admin
2. Use search combobox to search for a prompt
3. Click to add prompt to a group
4. Verify: prompt appears in group

### Generate Report
1. Login as admin
2. Navigate to a group with prompts
3. Click generate report
4. Verify: report preview shows
