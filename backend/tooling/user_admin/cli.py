"""Command line for the server account tool. See the package docstring and
PBL's runbook for its test sites (not part of this copy)."""

from __future__ import annotations

import argparse
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator, Sequence

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.modules.identity.password_rules import RULES_TEXT, password_problem

from . import service
from .database import SessionLocal
from .credentials import (
    MARK_INCOMPLETE,
    MARK_NOT_WRITTEN,
    MARK_WRITTEN,
    CredentialsFileError,
    generate_password,
    pending_credentials,
    require_credentials_location,
)
from .service import UserAdminError

# Exit statuses: 0 done, 1 a check that found a problem, 2 refused (nothing saved), 3 a change that
# may or may not have been saved, 130 interrupted before anything was saved.
EXIT_NOT_CONFIRMED = 3
EXIT_INTERRUPTED = 130

# What a later check can settle about a line in the credentials file. `list` says whether an
# account exists, so it settles a create; it never says which password an account has, so it
# cannot settle a reset.
ACTION_CREATED = "created"
ACTION_PASSWORD_RESET = "password reset"

# How many generated passwords to try for one that meets the rules (see _new_password).
GENERATED_PASSWORD_DRAWS = 20

# How long to keep asking whether a commit whose confirmation was lost took effect.
COMMIT_CHECK_ATTEMPTS = 10
COMMIT_CHECK_INTERVAL_SECONDS = 1.0


def _describe(user: service.UserSummary) -> str:
    state = "active" if user.is_active else "disabled"
    password = "" if user.has_password else ", no password"
    roles = ", ".join(user.role_codes) or "no roles"
    return f"{user.username} ({user.display_name}) - {state}{password} - {roles}"


def _database_refusal(exc: SQLAlchemyError) -> str:
    """Name a database failure without quoting it.

    A database error's text includes the failed statement's parameters, and for these commands one
    of them can be a password hash. Only its kind is reported.
    """
    if isinstance(exc, IntegrityError):
        return "the database refused a duplicate: a user with that name may already exist"
    return f"the database refused the change ({type(exc).__name__})"


@contextmanager
def _session() -> Iterator[Session]:
    """One session whose closing cannot speak.

    Closing can fail, and it happens on the way out of a block that may be handling a database
    error whose text carries the failed statement's parameters - for a password command, the
    generated hash among them. An exception from the close would come out with that error still in
    its exception chain, and Python prints the chain. Nothing is lost by staying quiet: the
    connection is returned or dropped either way, and the command keeps the exit status it had
    already decided on.

    `BaseException`, not `Exception`: a Ctrl+C landing here would escape and carry the same chain.
    Nothing is being waited for at this point, so swallowing it costs the operator nothing - the
    command has finished and is about to return.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        try:
            db.close()
        except BaseException:
            pass


def _rollback_quietly(db: Session) -> None:
    """End the transaction without letting the cleanup itself speak.

    These rollbacks run while a database error is being handled, and that error's text carries the
    failed statement's parameters - for a password command, the generated hash among them. A
    rollback that raised there would propagate with that error still in its exception chain, and
    Python would print the chain, hash and all. Nothing is lost by staying quiet: an uncommitted
    transaction is abandoned anyway when the connection closes.

    `BaseException`, not `Exception`: a Ctrl+C landing on the rollback would escape and carry the
    same chain. Ctrl+C still interrupts the substantive work above; it is only this last tidying
    step, after the outcome is already decided, that cannot be allowed to raise.
    """
    try:
        db.rollback()
    except BaseException:
        pass


def _refused(db: Session, message: str) -> int:
    _rollback_quietly(db)
    print(f"Refused: {message}", file=sys.stderr)
    return 2


# How to settle an exit 3: for most commands `list` shows the change. It shows neither of the two below, and running
# either again also acts on anything that happened since the first run, so each says exactly what a second run does.
SETTLE_BY_LIST = "Check with `list`; if it was not saved, run the command again."
SETTLE_END_SIGN_INS = (
    "`list` cannot show whether it was saved. Run the command again: if the first run was saved, the second also ends "
    "any sign-in made since, which only means signing in once more."
)
SETTLE_UNLOCK = (
    "`list` cannot show whether it was saved. If the person still cannot sign in, run the command again - knowing that "
    "a second run lifts whatever stop is then in force, including one made by wrong passwords since the first."
)


def _run(change: Callable[[Session], str], settle: str = SETTLE_BY_LIST) -> int:
    """Apply one change in one transaction. Anything refused is reported without a traceback.

    A commit can take effect even though the connection fails, or the command is interrupted, before
    it returns. The outcome is therefore looked up rather than assumed, as it is for a password
    change and for the same reason: telling the operator nothing was saved about a change that was
    saved would leave them wrong about who can sign in, or with which roles.
    """
    failure: BaseException | None = None  # what the commit raised, if it did not return normally
    outcome = None  # then: "committed", "aborted" or "unknown"
    refusal: str | None = None  # a refusal's message, kept so it can be reported clear of its cause
    with _session() as db:
        try:
            message = change(db)
            transaction_id = service.current_transaction_id(db)
            try:
                db.commit()
            except BaseException as exc:  # an interruption too: the commit may still have taken effect
                failure, outcome = exc, "unknown"
                outcome = _commit_outcome(db, transaction_id)
        except (UserAdminError, CredentialsFileError) as exc:
            refusal = str(exc)
        except SQLAlchemyError as exc:  # raised before the commit
            # Only the message is taken while this exception is the one being handled. Anything
            # else that raised here - an interruption above all - would come out with it as its
            # context, and Python prints the context chain.
            refusal = f"{_database_refusal(exc)}. Nothing was saved."
        except KeyboardInterrupt:
            if outcome is None:  # before the commit: nothing was saved
                _rollback_quietly(db)
                print("Interrupted: nothing was saved.", file=sys.stderr)
                return EXIT_INTERRUPTED
            # Interrupted again while the commit's outcome was being looked up.
        if refusal is not None:  # reported out here, clear of the exception that caused it
            return _refused(db, refusal)
    if outcome == "aborted":
        if isinstance(failure, SQLAlchemyError):
            print(f"Refused: {_database_refusal(failure)}. Nothing was saved.", file=sys.stderr)
            return 2
        print("Interrupted: nothing was saved.", file=sys.stderr)
        return EXIT_INTERRUPTED
    if outcome == "unknown":
        print(
            "Not confirmed: the database did not confirm the change, and could not be asked "
            f"afterwards whether it was saved. {settle}",
            file=sys.stderr,
        )
        return EXIT_NOT_CONFIRMED
    if outcome == "committed":
        cause = "The database connection failed" if isinstance(failure, SQLAlchemyError) else "Interrupted"
        message += f"\n{cause} as the change was saved; the database confirmed afterwards that it was."
    print(message)
    return 0


def _commit_outcome(db: Session, transaction_id: str) -> str:
    """After a commit raised: "committed", "aborted" or "unknown".

    A commit can take effect even though the connection fails before the database confirms it, so
    the error alone does not say whether the change was saved. PostgreSQL can be asked afterwards,
    from a new connection, what became of the transaction (`pg_xact_status`). A transaction still
    finishing its commit reports "in progress", so the question is repeated for a while.
    """
    _rollback_quietly(db)  # ends the transaction if the commit never reached the database
    for attempt in range(COMMIT_CHECK_ATTEMPTS):
        if attempt:
            time.sleep(COMMIT_CHECK_INTERVAL_SECONDS)
        try:
            with _session() as check:
                status = service.transaction_status(check, transaction_id)
        except SQLAlchemyError:
            continue
        if status in ("committed", "aborted"):
            return status
    return "unknown"


def _read_password_from_stdin() -> str:
    """The chosen password, read from standard input rather than the command line.

    Deliberately not an --password VALUE option: a value in argv is visible to `ps` while the
    command runs and lands in the operator's shell history, which is what the rest of this tool
    goes to some length to avoid. Read it from a pipe or a here-doc instead.

    One trailing newline is stripped, because echo and here-docs add one and nobody means it to be
    part of the password. Everything else is taken literally, so a password may contain spaces.
    """
    raw = sys.stdin.read()
    password = raw[:-1] if raw.endswith("\n") else raw
    if not password:
        raise CredentialsFileError(
            "No password on standard input. Pipe it in, for example:  "
            "printf %s '$PW' | ... create --username u --password-stdin ..."
        )
    if "\n" in password:
        raise CredentialsFileError(
            "The password contains a line break. The credentials file is one line per password, "
            "and a break would split the record."
        )
    # The application's own limit (identity/schemas.py: max_length=200). A longer password would be
    # written to the file and then refused at sign-in, which is the worst of both.
    if len(password) > 200:
        raise CredentialsFileError(f"The password is {len(password)} characters; the limit is 200.")
    return password


def _new_password(*, from_stdin: bool, username: str) -> str:
    """The password to set: the operator's, if it meets the rules (TB-1 TB1-204 part a), or a generated one.

    A generated password meets them by construction, unless it happens to contain a short username that is one of
    its words; a few more draws settle that.
    """
    if from_stdin:
        password = _read_password_from_stdin()
        problem = password_problem(password, username)
        if problem is not None:
            raise CredentialsFileError(f"That password cannot be used: {problem}. {RULES_TEXT}")
        return password
    for _ in range(GENERATED_PASSWORD_DRAWS):
        password = generate_password()
        if password_problem(password, username) is None:
            return password
    raise CredentialsFileError(
        "Could not generate a password that meets the rules for this username. Choose one with --password-stdin."
    )


def _run_with_new_password(
    *,
    action: str,
    username: str,
    credentials_file: str,
    apply: Callable[[Session, str], service.UserSummary],
    note: str = "",
    from_stdin: bool = False,
) -> int:
    path = Path(credentials_file)
    try:
        # Before any database change, so a file that would vanish with the container is never used.
        require_credentials_location(path)
    except CredentialsFileError as exc:
        print(f"Refused: {exc}", file=sys.stderr)
        return 2
    try:
        password = _new_password(from_stdin=from_stdin, username=username)
    except CredentialsFileError as exc:
        print(f"Refused: {exc}", file=sys.stderr)
        return 2
    failure: BaseException | None = None  # what the commit raised, if it did not return normally
    outcome = None  # then: "committed", "aborted" or "unknown"
    marked = MARK_NOT_WRITTEN  # whether the file itself ended up carrying the doubt
    refusal: str | None = None  # a refusal's message, kept so it can be reported clear of its cause
    with _session() as db:
        try:
            user = apply(db, hash_password(password))
            transaction_id = service.current_transaction_id(db)
            # The line is written and flushed before the commit, and removed only when the commit is
            # known not to have taken effect. No account ends up with a password that exists
            # nowhere; a line that may name a password its account does not have is reported.
            with pending_credentials(path, action=action, username=user.username, password=password) as pending:
                try:
                    db.commit()
                except BaseException as exc:  # an interruption too: the commit may still have taken effect
                    failure, outcome = exc, "unknown"
                    outcome = _commit_outcome(db, transaction_id)
                    if outcome == "aborted":
                        pending.remove()
                    elif outcome == "unknown":
                        # So a later reader of the file sees the doubt too, not only this output.
                        marked = pending.mark_unconfirmed()
        except (UserAdminError, CredentialsFileError) as exc:
            refusal = str(exc)
        except SQLAlchemyError as exc:  # raised before the commit
            # Only the message is taken while this exception is the one being handled. Anything
            # else that raised here - an interruption above all - would come out with it as its
            # context, and Python prints the context chain.
            refusal = f"{_database_refusal(exc)}. Nothing was saved."
        except KeyboardInterrupt:
            if outcome is None:  # before the commit: nothing was saved
                _rollback_quietly(db)
                print("Interrupted: nothing was saved.", file=sys.stderr)
                return EXIT_INTERRUPTED
            # Interrupted again while the commit's outcome was being looked up: the line stays.
        if refusal is not None:  # reported out here, clear of the exception that caused it
            return _refused(db, refusal)
    if outcome == "aborted":
        if isinstance(failure, SQLAlchemyError):
            print(
                f"Refused: {_database_refusal(failure)}. Nothing was saved and no password was kept.",
                file=sys.stderr,
            )
            return 2
        print("Interrupted: nothing was saved and no password was kept.", file=sys.stderr)
        return EXIT_INTERRUPTED
    if outcome == "unknown":
        kept = f"Its password line is kept in {credentials_file}, "
        if marked == MARK_WRITTEN:
            kept += "marked unconfirmed, in case it was."
        elif marked == MARK_NOT_WRITTEN:
            kept += (
                "but the note marking it unconfirmed was not reliably written there, so this "
                "message may be the only record of the doubt."
            )
        else:  # MARK_INCOMPLETE: part of the note is in the file without its newline
            kept += (
                f"but the note marking it unconfirmed was left half written, so {credentials_file} "
                "now ends in an incomplete `# unconfirmed:` line. Remove that incomplete last line "
                "by hand - not the password line above it, which is the one to check - because "
                "until then the next password command will refuse the file."
            )
        # `list` settles a create, because it says whether the account exists. It never says which
        # password an account has, so it cannot settle a reset: saying otherwise would invite handing
        # out a password that does not work while the old one still does.
        settle = (
            f"Check with `list`: if {user.username} is not there, nothing was saved, so run the command "
            "again, and its new line replaces this one."
            if action == ACTION_CREATED
            else "`list` cannot settle a reset: it shows that the account has some password, not which "
            "one. Sign in with the kept password to check it, or, once the database answers again, run "
            "reset-password and hand out only a password from a run that reported success."
        )
        print(
            f"Not confirmed: the database did not confirm the change to {user.username}, and could not "
            f"be asked afterwards whether it was saved. {kept} {settle}",
            file=sys.stderr,
        )
        return EXIT_NOT_CONFIRMED
    recovered = ""
    if outcome == "committed":
        cause = "The database connection failed" if isinstance(failure, SQLAlchemyError) else "Interrupted"
        recovered = f"\n{cause} as the change was saved; the database confirmed afterwards that it was."
    print(f"{_describe(user)}\nPassword written to {credentials_file}. It is not shown here.{recovered}{note}")
    return 0


def _read(report: Callable[[Session], int]) -> int:
    with _session() as db:
        try:
            return report(db)
        except SQLAlchemyError as exc:
            # Only the message is taken while this exception is the one being handled. Anything
            # else that raised here - an interruption above all - would come out with it as its
            # context, and Python prints the context chain.
            kind = type(exc).__name__
        print(f"Could not read the users ({kind}).", file=sys.stderr)
        return 2


def _cmd_list(args: argparse.Namespace) -> int:
    def report(db: Session) -> int:
        users = service.list_users(db)
        for user in users:
            print(_describe(user))
        print(f"{len(users)} user(s).")
        return 0

    return _read(report)


def _cmd_create(args: argparse.Namespace) -> int:
    return _run_with_new_password(
        action=ACTION_CREATED,
        username=args.username,
        credentials_file=args.credentials_file,
        apply=lambda db, password_hash: service.create_user(
            db,
            username=args.username,
            display_name=args.display_name,
            role_codes=args.role,
            password_hash=password_hash,
        ),
        from_stdin=args.password_stdin,
    )


def _cmd_reset_password(args: argparse.Namespace) -> int:
    return _run_with_new_password(
        action=ACTION_PASSWORD_RESET,
        username=args.username,
        credentials_file=args.credentials_file,
        apply=lambda db, password_hash: service.set_password_hash(
            db, username=args.username, password_hash=password_hash
        ),
        from_stdin=args.password_stdin,
        note="\nEvery sign-in made before this reset has ended.",
    )


def _cmd_set_roles(args: argparse.Namespace) -> int:
    return _run(lambda db: _describe(service.set_roles(db, username=args.username, role_codes=args.role)))


def _cmd_disable(args: argparse.Namespace) -> int:
    return _run(
        lambda db: f"{_describe(service.set_active(db, username=args.username, active=False))}\n"
        "Takes effect at once, including for anyone already signed in, and enabling the account again "
        "does not bring those sign-ins back."
    )


def _cmd_end_sign_ins(args: argparse.Namespace) -> int:
    return _run(
        lambda db: f"{_describe(service.end_sign_ins(db, username=args.username))}\n"
        "Every sign-in this account had has ended; its password is unchanged.",
        settle=SETTLE_END_SIGN_INS,
    )


def _cmd_unlock(args: argparse.Namespace) -> int:
    def change(db: Session) -> str:
        if service.unlock_sign_in(db, username=args.username):
            return f"{args.username} may sign in again."
        return f"{args.username} was not stopped from signing in; nothing changed."

    return _run(change, settle=SETTLE_UNLOCK)


def _cmd_enable(args: argparse.Namespace) -> int:
    def change(db: Session) -> str:
        user = service.set_active(db, username=args.username, active=True)
        note = "" if user.has_password else "\nThis account has no password; use reset-password before it can sign in."
        return _describe(user) + note

    return _run(change)


def _cmd_retire_demo_users(args: argparse.Namespace) -> int:
    def change(db: Session) -> str:
        retired = service.retire_users(db, service.DEMO_USERNAMES)
        lines = [f"Retired {_describe(user)}" for user in retired]
        lines.append(
            f"{len(retired)} demo user(s) retired. The others were missing or already retired."
            if len(retired) < len(service.DEMO_USERNAMES)
            else f"{len(retired)} demo user(s) retired."
        )
        return "\n".join(lines)

    return _run(change)


def _cmd_seed_demo_users(args: argparse.Namespace) -> int:
    settings = get_settings()
    if not settings.is_development_environment:
        print(
            f"Refused: APP_ENV={settings.app_env!r} is not a development environment. The demo users "
            f"sign in with the published password, so they are created only for development and CI "
            f"(TB-1 TB1-203). Nothing was saved.",
            file=sys.stderr,
        )
        return 2

    def change(db: Session) -> str:
        changed = service.seed_demo_users(db)
        if not changed:
            return f"The {len(service.DEMO_USERS)} demo users were already in place."
        return f"{len(changed)} demo user(s) created or restored: {', '.join(changed)}."

    return _run(change)


def _cmd_check_default_passwords(args: argparse.Namespace) -> int:
    def report(db: Session) -> int:
        offenders = service.users_accepting_password(db, service.DEMO_PASSWORD)
        if offenders:
            print("These active accounts still accept the demo password: " + ", ".join(offenders), file=sys.stderr)
            return 1
        print("No active account accepts the demo password.")
        return 0

    return _read(report)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tooling.user_admin",
        description="Manage CRM application users on the server. Passwords go only to the credentials file.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("list", help="List users, their state and roles.").set_defaults(handler=_cmd_list)

    create = commands.add_parser("create", help="Create a user with a generated password.")
    create.add_argument("--username", required=True)
    create.add_argument("--display-name", required=True)
    create.add_argument("--role", action="append", required=True, help="Role code; repeat for several.")
    create.add_argument(
        "--credentials-file",
        required=True,
        help="Root-only file the password is appended to, directly in /credentials (the server's secrets "
        "folder, mounted): new, or one this tool created.",
    )
    create.add_argument("--password-stdin", action="store_true", help="Read the password from standard input instead of generating one. Never pass a password as an option: argv is visible to ps and lands in shell history.")
    create.set_defaults(handler=_cmd_create)

    reset = commands.add_parser("reset-password", help="Give a user a new generated password.")
    reset.add_argument("--username", required=True)
    reset.add_argument("--credentials-file", required=True)
    reset.add_argument("--password-stdin", action="store_true", help="Read the password from standard input instead of generating one. Never pass a password as an option: argv is visible to ps and lands in shell history.")
    reset.set_defaults(handler=_cmd_reset_password)

    set_roles = commands.add_parser("set-roles", help="Replace a user's roles.")
    set_roles.add_argument("--username", required=True)
    set_roles.add_argument("--role", action="append", required=True)
    set_roles.set_defaults(handler=_cmd_set_roles)

    for name, handler, text in (
        ("disable", _cmd_disable, "Stop a user signing in, at once."),
        ("enable", _cmd_enable, "Let a disabled user sign in again."),
        ("end-sign-ins", _cmd_end_sign_ins, "End every sign-in a user has, keeping the password."),
        (
            "unlock",
            _cmd_unlock,
            "Let a username stopped after repeated wrong passwords sign in again before its stop runs out.",
        ),
    ):
        command = commands.add_parser(name, help=text)
        command.add_argument("--username", required=True)
        command.set_defaults(handler=handler)

    commands.add_parser(
        "retire-demo-users",
        help=f"Disable the demo users ({', '.join(service.DEMO_USERNAMES)}) and remove their passwords.",
    ).set_defaults(handler=_cmd_retire_demo_users)

    commands.add_parser(
        "seed-demo-users",
        help=f"Development and CI only: make the demo users ({', '.join(service.DEMO_USERNAMES)}) "
        f"active with the demo password. Refused outside a development APP_ENV.",
    ).set_defaults(handler=_cmd_seed_demo_users)

    commands.add_parser(
        "check-default-passwords",
        help="Exit 1 if any active account still accepts the demo password.",
    ).set_defaults(handler=_cmd_check_default_passwords)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except SQLAlchemyError as exc:
        # A last resort, not a working path: every command catches its own database errors and
        # reports them by kind, and the two places cleanup could still have raised - the rollback
        # while an error is being handled, and closing the session - are quiet now. If something
        # unforeseen still gets here it is reported by kind rather than printed as a traceback,
        # because that traceback would carry the error's text and the text of anything left in its
        # exception chain, which for these commands can include a password hash. The status is the
        # conservative one: whatever reached here touched the database, so nothing can be claimed
        # about what was saved.
        print(
            f"Failed: the database call did not complete ({type(exc).__name__}). If the command "
            "changes something, whether it was saved is unknown; settle it the way the runbook "
            "settles an exit 3 for that command.",
            file=sys.stderr,
        )
        return EXIT_NOT_CONFIRMED
