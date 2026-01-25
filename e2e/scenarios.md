# E2E Verification Scenarios

Run these scenarios using Playwright MCP tools after docker-compose and frontend are up.

## Scenario 1: Login Flow
1. Navigate to http://localhost:5173
2. Fill email: admin@example.com, password: changethis
3. Click "Log in"
4. Verify: redirected to dashboard, see "$5.00" balance

## Scenario 2: Admin Navigation
1. After login, click "Admin" in sidebar navigation
2. Verify: Admin page loads with tabs (Users, Prompts, Approvals)
3. Verify: "Prompts" tab is accessible

## Scenario 3: Reference Data Loading (Tests Reference Router)
1. After admin login, go to Admin page
2. Click "Prompts" tab
3. Verify: Business Domains dropdown loads with options
4. Verify: Countries dropdown loads with options
5. Select a business domain and country
6. Verify: Topics list loads (may be empty if no topics exist)

## Scenario 4: Create Topic (Tests TopicService)
1. After admin login, go to Admin → Prompts tab
2. Click "Create New Topic" button
3. Fill form:
   - Title: "Test Topic E2E"
   - Description: "Test topic created via E2E"
   - Select any Business Domain
   - Select any Country
4. Click "Create" button
5. Verify: Success message appears
6. Verify: New topic appears in topics dropdown

## Scenario 5: Regular User Login (No Onboarding)
1. Navigate to http://localhost:5173
2. Fill email: user@example.com, password: changethis
3. Click "Log in"
4. Verify: redirected to onboarding page
5. Click "Get Started"
6. Select country (e.g., Ukraine), skip industry selection
7. Click "Continue" - verify it proceeds without industry
8. Fill brand name (e.g., "TestBrand")
9. Click "Continue", then "Finish Setup"
10. Verify: dashboard loads with "$5.00" balance shown

## Scenario 6: Generate Gemini Report

**Prerequisites:** User logged in, group with prompts exists

1. Navigate to Dashboard (http://localhost:5173)
2. Login as admin@example.com if not already logged in
3. Create a new group or open an existing group with prompts
4. Click "Generate Report" on the group
5. Select "Gemini" from AI Assistant dropdown
6. Verify: Gemini logo appears next to the selection
7. Click "Generate" button
8. Verify: Report generation starts (loading indicator shown)
9. Wait for report to complete
10. Verify: Report appears in history with Gemini logo and assistant name "Gemini"

