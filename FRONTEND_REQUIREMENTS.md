# Frontend Implementation Requirements: Manual Accreditation Notifications

This document outlines the requirements for implementing the manual email trigger feature on the Schools management page.

## 1. API Integration

- **Endpoint**: `POST /api/v1/schools/send-manual-emails` (or `/schools/send-manual-emails` if using the base router)
- **Authentication**: Bearer Token (HQ/Admin roles only)
- **Request Body**:
```json
{
  "schools": [
    { "code": "SC123", "type": "SSCE" },
    { "code": "SC456", "type": "BECE" }
  ]
}
```

## 2. UI/UX Requirements

### Schools List Table
1.  **Selection**: Add a checkbox column to the left of the school list.
2.  **Toggle All**: Add a "Select All" checkbox in the table header.
3.  **State Management**: Track the selected school codes and their types (SSCE vs BECE).

### Action Bar (Head Office View)
1.  **Button**: Add a button labeled **"Send Emails to School"**.
2.  **Visibility**: This button should only be visible/enabled for users with `HQ` or `Admin` roles.
3.  **Disabled State**: The button should be disabled if no schools are selected.

### Confirmation Dialog
When the button is clicked, show a modal/dialog with:
1.  **Summary**: Display the number of selected schools (e.g., "Send emails to 5 selected schools?").
2.  **Submit Button**: "Send Notifications".
3.  **Cancel Button**: Close the modal.

### Feedback
1.  **Loading State**: Show a spinner or progress indicator while the request is in progress.
2.  **Success Notification**: Show a success toast if all emails were processed.
3.  **Error Handling**: If some emails failed, display a summary of the results returned by the API (the API returns a `results` array with the status for each school).

## 3. Email CC
No frontend action is required for the CC. The backend automatically CCs `accreditation@neco.gov.ng` for every email sent via this endpoint.
