# 10 - Hosting, users and targets

Where the CRM will run, how many people will use it, and what it must achieve. Each figure is marked:
**PBL** - decided by PBL; **You propose** - we ask you to state it in your proposal.

## Hosting

| Item | Figure | Status |
| --- | --- | --- |
| Where | PBL's own Microsoft Azure account. You may propose another cloud in your proposal; if PBL accepts it, it becomes the agreed hosting. Once hosting is set up, moving it to another cloud is a change request | PBL |
| Setting it up | Part of this package: production in Azure, the automatic deployment, backups and monitoring, and handing all of it over to PBL with written instructions | PBL |
| A test environment | A second, smaller environment in Azure for PBL's user testing before each release | PBL |
| Support after go-live | Quoted separately, as a monthly figure | PBL |
| Database | Azure's managed PostgreSQL, so that backups and restores are Azure's service rather than our own scripts. Version 17 today; you may propose a later version, and if you do, you carry out the move and prove it: every migration from an empty database, every test, and an upgrade of a copy of real data | PBL |
| Who owns what | PBL owns the Azure account, the code, the data and every password; you work in it with the access PBL gives you | PBL |

Where this page says Azure, read the cloud PBL accepts, if it accepts another.

## Users

| Item | Figure | Status |
| --- | --- | --- |
| Users now | Under 10 | PBL |
| Users in two to three years | About 25 | PBL |
| Using it at the same time | About 5 | PBL |
| Design and test for | Double: 50 users, 10 at the same time | PBL |
| Growing beyond that | Should need a larger Azure plan, not a rebuild. Tell us where that stops being true | You propose |
| Where users are | India; the system works in India's time | PBL |
| Devices | A desktop or laptop browser (current Chrome and Edge). A phone layout is later | PBL |

## What it must achieve

| Item | Target | Status |
| --- | --- | --- |
| Speed | 95% of ordinary actions answered within 2 seconds at the "design and test for" numbers above | PBL |
| Availability | 99.5% a month, measured during India's working hours; planned maintenance outside them and announced in advance | PBL |
| Backups | Continuous, kept for 30 days, so the database can be restored to any moment in the last 30 days | PBL |
| Restore shown before go-live | A full restore into a separate environment, in front of PBL, before go-live | PBL |
| Data lost in a failure (RPO) | No more than 15 minutes | PBL |
| Back in service after a failure (RTO) | Within 4 hours | PBL |
| How long records are kept | A setting; PBL will set the periods (doc 03, group H) | PBL |
| Connections | Encrypted (TLS 1.2 or later); data encrypted where it is stored | PBL's requirements |
| Sign-in | Strong passwords, lock-out after failed attempts and a session time-out that is a setting; single sign-on and a two-step sign-in are a separately priced option | PBL |
| Monitoring | An alert to the named support contact when the site or the database stops answering; errors logged in a way support can search | PBL |
| Support response | Response and resolution times by priority, and who to call when | You propose |
| Data volumes | How many Accounts, offers and documents your design assumes over five years | You propose |

The speed, availability and security targets come from PBL's non-functional requirements
(`docs/source/current/requirements/PBL_ERP_Non_Functional_Requirements_2026-05-19.docx`, read through
`docs/reference/erp-source-extracts/ERP_NFR_FULL_TEXT_EXTRACT.md`) and the baseline in
`docs/agent/architecture/NFR_BASELINE_AND_VERIFICATION.md`. Where those documents ask for more than this page - for
example structured access down to branch or field level, or a phone layout - this page sets what applies to this
package, and the rest is later work.

## What we will check before go-live

That each figure above is met, with evidence: a timing run at the "design and test for" load, the restore
demonstration, the monitoring alert seen firing, and the security items in annex A marked B corrected. This is part of
the go-live work in doc 03, group B.
