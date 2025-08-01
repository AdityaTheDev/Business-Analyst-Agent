from typing import Optional 
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os
import re
import json
from datetime import datetime

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.units import inch


def get_next_filename(base_name="brd", ext="pdf", folder="reports"):
    os.makedirs(folder, exist_ok=True)
    existing_files = os.listdir(folder)
    
    version_pattern = re.compile(rf"{re.escape(base_name)}_v(\d+)\.{ext}")
    versions = [
        int(match.group(1)) 
        for f in existing_files 
        if (match := version_pattern.match(f))
    ]
    
    next_version = max(versions, default=0) + 1
    return os.path.join(folder, f"{base_name}_v{next_version}.{ext}")

def save_logs(pdf_filename, brd_text):
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    folder_name = os.path.join(root_dir, 'logs')
    os.makedirs(folder_name,exist_ok=True)
    log_file = os.path.join(folder_name,"brd_log.json")
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "pdf": pdf_filename,
        "brd_text": brd_text
    }

    # Load existing logs
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            logs = json.load(f)
    else:
        logs = []

    logs.append(log_entry)

    # Save updated logs
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)
    print("The logs saved sucessfully in :",log_file)


def markdown_to_paragraphs(markdown_text: str, styles) -> list:
    """
    Converts basic markdown text to a list of reportlab flowables (Paragraph, Spacer, List).
    """
    flowables = []
    lines = markdown_text.strip().split('\n')
    bullet_items = []
    numbered_items = []

    for line in lines:
        line = line.strip()

        # Handle headers
        if line.startswith('####'):
            flowables.append(Paragraph(f"<b>{line[4:].strip()}</b>", styles['MyHeading4']))
        elif line.startswith('###'):
            flowables.append(Paragraph(f"<b>{line[3:].strip()}</b>", styles['MyHeading3']))
        elif line.startswith('##'):
            flowables.append(Paragraph(f"<b>{line[2:].strip()}</b>", styles['MyHeading2']))
        elif line.startswith('#'):
            flowables.append(Paragraph(f"<b>{line[1:].strip()}</b>", styles['MyHeading1']))

        # Handle bullet list
        elif line.startswith('- '):
            bullet_items.append(Paragraph(markdown_inline_to_html(line[2:].strip()), styles['Normal']))
        elif re.match(r'^\d+\.\s+', line):
            numbered_items.append(Paragraph(markdown_inline_to_html(re.sub(r'^\d+\.\s+', '', line)), styles['Normal']))

        # Empty line
        elif line == "":
            # Flush bullet list if any
            if bullet_items:
                flowables.append(ListFlowable(
                    [ListItem(b, leftIndent=20) for b in bullet_items],
                    bulletType='bullet', start='-', leftIndent=20))
                bullet_items = []
            if numbered_items:
                flowables.append(ListFlowable(
                    [ListItem(n, leftIndent=20) for n in numbered_items],
                    bulletType='1', leftIndent=20))
                numbered_items = []
            flowables.append(Spacer(1, 12))

        # Normal paragraph
        else:
            flowables.append(Paragraph(markdown_inline_to_html(line), styles['Normal']))

    # Flush remaining list items
    if bullet_items:
        flowables.append(ListFlowable([ListItem(b, leftIndent=20) for b in bullet_items],
                                      bulletType='bullet', start='-', leftIndent=20))
    if numbered_items:
        flowables.append(ListFlowable([ListItem(n, leftIndent=20) for n in numbered_items],
                                      bulletType='1', leftIndent=20))

    return flowables


def markdown_inline_to_html(text: str) -> str:
    """
    Convert inline markdown (**bold**, *italic*, __underline__) to HTML-style for Paragraph.
    """
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    text = re.sub(r'__(.*?)__', r'<u>\1</u>', text)
    return text


def save_report(report: str) -> str:
    """
    Converts a BRD (Business Requirement Document) string into a formatted PDF file 
    and saves it with an auto-incremented versioned filename (e.g., brd_v1.pdf, brd_v2.pdf, etc.).

    Args:
        report (str): The full text content of the BRD to be included in the PDF.

    Returns:
        str: The file path of the saved PDF document.
    """
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    text_output_folder = os.path.join(root_dir, 'Text_Output')
    os.makedirs(text_output_folder, exist_ok=True)
    text_filename="brd_doc.txt"
    text_output_path = os.path.join(text_output_folder, text_filename)

    with open(text_output_path,'w') as f:
        f.write(report)

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    output_folder = os.path.join(root_dir, 'Output')
    os.makedirs(output_folder, exist_ok=True)
    filename=get_next_filename(base_name="BRD",ext="pdf",folder=output_folder)
    output_path = os.path.join(output_folder, filename)

    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            rightMargin=50, leftMargin=50,
                            topMargin=50, bottomMargin=50)

    # Styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='MyHeading1', parent=styles['Heading1'], fontSize=18, spaceAfter=12))
    styles.add(ParagraphStyle(name='MyHeading2', parent=styles['Heading2'], fontSize=16, spaceAfter=10))
    styles.add(ParagraphStyle(name='MyHeading3', parent=styles['Heading3'], fontSize=14, spaceAfter=8))
    styles.add(ParagraphStyle(name='MyHeading4', parent=styles['Heading4'], fontSize=12, spaceAfter=6))
    styles.add(ParagraphStyle(name='MyNormal',    parent=styles['Normal'],  fontSize=10, spaceAfter=6, alignment=TA_LEFT))

    story = markdown_to_paragraphs(report, styles)
    doc.build(story)

    print("Report saved in path:", output_path)
    save_logs(filename,report)
    return output_path


def save_user_manual(report: str) -> str:
    """
    Converts a user manual report string into a formatted PDF file 
    and saves it with an auto-incremented versioned filename (e.g., user_manual_v1.pdf, user_manual_v2.pdf, etc.).

    Args:
        report (str): The full text content of the user manual to be included in the PDF.

    Returns:
        str: The file path of the saved PDF document.
    """
    # root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    # text_output_folder = os.path.join(root_dir, 'Text_Output')
    # os.makedirs(text_output_folder, exist_ok=True)
    # text_filename="brd_doc.txt"
    # text_output_path = os.path.join(text_output_folder, text_filename)

    # with open(text_output_path,'w') as f:
    #     f.write(report)

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    output_folder = os.path.join(root_dir, 'User_Manual')
    os.makedirs(output_folder, exist_ok=True)
    filename=get_next_filename(base_name="user_manual",ext="pdf",folder=output_folder)
    output_path = os.path.join(output_folder, filename)

    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            rightMargin=50, leftMargin=50,
                            topMargin=50, bottomMargin=50)

    # Styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='MyHeading1', parent=styles['Heading1'], fontSize=18, spaceAfter=12))
    styles.add(ParagraphStyle(name='MyHeading2', parent=styles['Heading2'], fontSize=16, spaceAfter=10))
    styles.add(ParagraphStyle(name='MyHeading3', parent=styles['Heading3'], fontSize=14, spaceAfter=8))
    styles.add(ParagraphStyle(name='MyHeading4', parent=styles['Heading4'], fontSize=12, spaceAfter=6))
    styles.add(ParagraphStyle(name='MyNormal',    parent=styles['Normal'],  fontSize=10, spaceAfter=6, alignment=TA_LEFT))

    story = markdown_to_paragraphs(report, styles)
    doc.build(story)

    print("Report saved in path:", output_path)
    save_logs(filename,report)
    return output_path

def save_usecase_acceptance_criteria(report: str) -> str:
    """
    Converts a Use Case and Acceptance Criteria string into a formatted PDF file 
    and saves it with an auto-incremented versioned filename (e.g., use_case_v1.pdf, use_case_v2.pdf, etc.).

    Args:
        report (str): The full text content of the Use Case and Acceptance Criteria to be included in the PDF.

    Returns:
        str: The file path of the saved PDF document.
    """
    # root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    # text_output_folder = os.path.join(root_dir, 'Text_Output')
    # os.makedirs(text_output_folder, exist_ok=True)
    # text_filename="brd_doc.txt"
    # text_output_path = os.path.join(text_output_folder, text_filename)

    # with open(text_output_path,'w') as f:
    #     f.write(report)

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    output_folder = os.path.join(root_dir, 'Usecase')
    os.makedirs(output_folder, exist_ok=True)
    filename=get_next_filename(base_name="Usecase",ext="pdf",folder=output_folder)
    output_path = os.path.join(output_folder, filename)

    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            rightMargin=50, leftMargin=50,
                            topMargin=50, bottomMargin=50)

    # Styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='MyHeading1', parent=styles['Heading1'], fontSize=18, spaceAfter=12))
    styles.add(ParagraphStyle(name='MyHeading2', parent=styles['Heading2'], fontSize=16, spaceAfter=10))
    styles.add(ParagraphStyle(name='MyHeading3', parent=styles['Heading3'], fontSize=14, spaceAfter=8))
    styles.add(ParagraphStyle(name='MyHeading4', parent=styles['Heading4'], fontSize=12, spaceAfter=6))
    styles.add(ParagraphStyle(name='MyNormal',    parent=styles['Normal'],  fontSize=10, spaceAfter=6, alignment=TA_LEFT))

    story = markdown_to_paragraphs(report, styles)
    doc.build(story)

    print("Report saved in path:", output_path)
    save_logs(filename,report)
    return output_path

if __name__=="__main__":
    report="""
    
3

# Business Requirements Document: Leave Approval System
## 1. Title Page
**Project Name:** Leave Approval System
**Client:** [Client Name]
**Date:** October 26, 2023
**Version:** 1.0
## 2. Table of Contents
1.  Title Page
2.  Table of Contents
3.  Executive Summary
4.  Business Objective
5.  Background
6.  Scope
7.  Stakeholders
8.  Requirements
9.  Assumptions and Constraints
10. Success Metrics
11. Timeline or Milestones
12. Appendix
## 3. Executive Summary
This document outlines the business requirements for a new Leave Approval System. This system will automate and streamline the leave request and approval process, integrating with the existing HRMS to provide employees with self-service access to leave information and managers with an efficient approval workflow.  The initial rollout will target three departments, with a Q4 launch.
## 4. Business Objective
The primary objective is to automate the leave approval process, reducing administrative overhead and improving efficiency. This will also empower employees with self-service access to their leave information, leading to increased satisfaction.
## 5. Background
The current leave approval process is manual and time-consuming. This leads to delays in approvals, increased administrative burden, and lack of visibility for employees regarding their leave status and balances.  The new system aims to address these challenges by providing an automated, transparent, and user-friendly solution.
## 6. Scope
### 6.1 In-Scope
*   Employee submission of leave requests.
*   Manager approval/rejection of leave requests.
*   Integration with existing HRMS for employee data and leave balances.
*   Automated notifications for leave requests and approvals.
*   Employee access to leave history and balance information.
*   Browser-based and mobile-friendly interface.
*   Reporting on leave trends.
*   Support for various leave types (e.g., vacation, sick leave).
*   Role-based access control (employees, managers).
*   Initial rollout to 3 departments.
### 6.2 Out-of-Scope
*   Payroll integration (initially).
*   Advanced reporting and analytics beyond basic leave trends.
*   Integration with other systems besides HRMS.
*   Support for external contractors (initially).
## 7. Stakeholders
*   Employees: End-users of the system who will submit leave requests and view their leave information.
*   Managers: Responsible for approving or rejecting leave requests.
*   HR Department: Oversees the leave approval process and manages system configuration.
*   IT Department: Responsible for system implementation, maintenance, and support.
*   Project Sponsor: [Name/Title] - Provides overall project guidance and funding.
## 8. Requirements
### 8.1 Functional Requirements
*   **REQ-1:** The system shall allow employees to submit leave requests online.
*   **REQ-2:** The system shall automatically route leave requests to the employee's manager for approval.
*   **REQ-3:** Managers shall be able to approve or reject leave requests with comments.
*   **REQ-4:** The system shall send automated notifications to employees regarding the status of their leave requests.
*   **REQ-5:** The system shall display employees' current leave balances.
*   **REQ-6:** The system shall maintain a history of all leave requests and approvals for each employee.
*   **REQ-7:** The system shall integrate with the existing HRMS to retrieve employee data and update leave balances.
*   **REQ-8:** The system shall support different leave types (e.g., vacation, sick leave, personal leave).
*   **REQ-9:** The system shall provide role-based access control, ensuring that only authorized users can access specific functionalities.
*   **REQ-10:** The system shall generate reports on leave trends, such as total leave days taken per department.
### 8.2 Non-Functional Requirements
*   **NFR-1:** The system shall be accessible via a web browser and be mobile-friendly.
*   **NFR-2:** The system shall be secure and protect sensitive employee data.
*   **NFR-3:** The system shall be user-friendly and easy to navigate.
*   **NFR-4:** The system shall be reliable and available during business hours.
*   **NFR-5:** The system shall be scalable to accommodate future growth.
*   **NFR-6:** The system should have a response time of less than 3 seconds for all common operations.
## 9. Assumptions and Constraints
*   **Assumption 1:** The existing HRMS has a well-defined API for integration.
*   **Assumption 2:** All employees have access to a computer or mobile device with internet connectivity.
*   **Constraint 1:** The project must be completed within the allocated budget.
*   **Constraint 2:** The system must be compliant with all relevant data privacy regulations.
*   **Constraint 3:** The system needs to be launched in Q4.
## 10. Success Metrics

*   Reduced time for leave approval process (e.g., from 5 days to 1 day).
*   Increased employee satisfaction with the leave process (measured through surveys).
*   Reduced administrative overhead for HR department (measured by time savings).
*   Improved accuracy of leave data.
*   High system adoption rate among employees and managers.
## 11. Timeline or Milestones
*   **Phase 1: Requirements Gathering and Design (2 weeks)**
*   **Phase 2: Development (6 weeks)**
*   **Phase 3: Testing (2 weeks)**
*   **Phase 4: Deployment and Training (2 weeks)**
*   **Go-Live: Q4**
## 12. Appendix
*   [Optional: Include any supporting documents, such as process flow diagrams or data dictionaries.]
    """
    log_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs", "brd_log.json"))
    with open(log_path,'r') as f:
        data=json.load(f)
    print(data[-1]['brd_text'])
    save_report(data[-1]['brd_text'])
    # root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    # output_folder = os.path.join(root_dir, 'Output')
    # os.makedirs(output_folder, exist_ok=True)
    # filename=get_next_filename(base_name="BRD",ext="pdf",folder=output_folder)
    # save_logs(filename,"Iam Yogesh")