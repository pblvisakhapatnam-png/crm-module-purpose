"""Generated passwords, and the root-only file they are written to.

The tool runs as root in a one-off container (`compose.sh run --rm`), so the file it writes to is
checked before anything is written. It must be a plain file name directly in CREDENTIALS_DIR, the
server's secrets folder mounted into the container: anywhere else it would vanish with the
container, or land in storage not meant for secrets, while the database keeps the new password. It
must be new or one this tool created (its first line is the tool's signature, so an existing empty
file is refused too), a regular file with no other hard link, not reached through a symbolic link. A
mistyped path, such as the site-login recovery file, is refused rather than appended to.

The file is opened relative to the folder itself, through a directory descriptor, so no directory
component of the name is ever followed: checking the text of a path is not enough, because
`/credentials/link/../name` normalises to `/credentials` while the kernel, following `link` first,
lands somewhere else entirely.
"""

from __future__ import annotations

import fcntl
import os
import secrets
import stat
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

# Letters and digits a tester can read off a printout and type on a phone: no 0/O, 1/l/I.
READABLE_CHARACTERS = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
GROUP_COUNT = 4
GROUP_LENGTH = 4

# Two words, a symbol and three digits - for example `Timber@Falcon637`. Chosen over the four
# random groups above for the CRM pilot, on the project owner's decision of 13 September 2026,
# because testers were finding a 19-character random string awkward to be given and to type.
#
# This is a deliberate and substantial reduction in strength: about 24 bits against about 92. At
# the request rate the pilot's Traefik rate limit allows, the whole space could be walked in
# somewhere around a day and a half by someone who had ALREADY passed the shared site login. It is
# accepted for a one-week pilot on synthetic data behind that login, on a temporary host, for a
# handful of named testers. **It is not suitable once real customer data is in the system**; at
# that point restore the four-group form, which is the same one-line change in reverse.
#
# The words are capped at six characters, so a password is at most 16 characters against the 19 of
# the form above - being shorter was the point. Unlike READABLE_CHARACTERS they are NOT filtered
# for look-alikes, and they do not need to be: `l`, `I` and `O` are ambiguous only in isolation,
# and inside a word the reader has the whole word to go on. They carry no meaning anyone could tie
# to a person or a username - a password derived from its own username, such as the "I am sales
# user 1" shape that prompted this, would be guessable by anyone who knew the username, which is a
# worse fault than being long.
PASSWORD_WORDS = (
    "Amber Anchor Apple Arrow Aspen Atlas Bamboo Banjo Basalt Beacon Birch "
    "Bison Brass Bronze Canvas Cedar Chalk Cobalt Copper Coral Cotton Dahlia "
    "Delta Denim Ember Fable Falcon Fennel Fern Flint Forest Fossil Garnet "
    "Ginger Hazel Heron Indigo Ivory Jasper Larch Laurel Ledger Lichen Linen "
    "Lotus Lumber Magnet Maple Marble Marlin Meadow Mica Mint Mosaic Moss "
    "Nectar Nickel Nutmeg Ochre Onyx Opal Orchid Osprey Otter Pebble Pewter "
    "Pine Plover Pollen Poplar Quarry Quartz Quill Raven Reed Ridge Rowan "
    "Rubble Sage Shale Sienna Silver Slate Sorrel Spruce Sumac Summit Teak "
    "Thorn Timber Topaz Tundra Valley Velvet Walnut Willow Yarrow Zinnia "
).split()
PASSWORD_SYMBOLS = "@#%+"
PASSWORD_DIGITS = 3

# The only folder a credentials file may be in: the server's secrets folder, mounted here by the
# runbook's `$ADMIN` command.
CREDENTIALS_DIR = Path("/credentials")

# The first line of every file this tool creates, and the test for "this tool created it".
CREDENTIALS_FILE_SIGNATURE = "# PBL CRM pilot sign-in passwords, written by backend/tooling/user_admin.\n"
CREDENTIALS_FILE_HEADER = (
    CREDENTIALS_FILE_SIGNATURE
    + "# Keep this file root-only (mode 0600). Columns: time (UTC), action, username, password.\n"
    + "# A line is that account's password once the command that wrote it reported success, and the\n"
    + "# last such line is the current one. A password command that exits 3 (not confirmed), or\n"
    + "# one that was killed, can leave a line to check first; the tool marks the ones it knows\n"
    + "# about with '# unconfirmed:' on the next line, and says in its own output when it could\n"
    + "# not write that mark. Sign in with a line to check it: `list` says whether the account\n"
    + "# exists, never which password it has.\n"
)

UNCONFIRMED_MARK = "# unconfirmed:"

# What the file holds after mark_unconfirmed(), for the caller's message.
MARK_WRITTEN = "written"
MARK_NOT_WRITTEN = "not written"  # or written without reaching the disk: no record to rely on
MARK_INCOMPLETE = "incomplete"  # note text without its newline: the file ends mid-line

# Indirections so a test can make a write, a flush or a cut-back fail, or stand in for a
# mounted folder.
_write = os.write
_fsync = os.fsync
_ftruncate = os.ftruncate
_is_mount = os.path.ismount


class CredentialsFileError(RuntimeError):
    """Raised when the credentials file cannot be written safely."""


def generate_password() -> str:
    """Two words, a symbol and three digits, for example `Timber@Falcon637`.

    About 24 bits from `secrets` - see PASSWORD_WORDS for why that is accepted for this pilot and
    when it must be reverted. The two words are always different, so a password never reads as a
    doubled word, which looks like a mistake to whoever is given it.
    """
    first, second = secrets.SystemRandom().sample(PASSWORD_WORDS, 2)
    symbol = secrets.choice(PASSWORD_SYMBOLS)
    digits = "".join(secrets.choice("0123456789") for _ in range(PASSWORD_DIGITS))
    return f"{first}{symbol}{second}{digits}"


def generate_high_entropy_password() -> str:
    """Four groups of four, for example `k7Qm-3xRt-...`: about 92 bits from `secrets`.

    Kept as the form to return to when the system holds anything but synthetic pilot data.
    """
    return "-".join(
        "".join(secrets.choice(READABLE_CHARACTERS) for _ in range(GROUP_LENGTH))
        for _ in range(GROUP_COUNT)
    )


def require_credentials_location(path: Path) -> None:
    """Refuse a credentials file anywhere but directly in CREDENTIALS_DIR, a mounted folder."""
    folder = CREDENTIALS_DIR
    if not path.is_absolute() or ".." in path.parts or not path.name or path.parent != folder:
        raise CredentialsFileError(
            f"The credentials file must be directly in {folder}, the server's secrets folder mounted "
            f"into this container, named without any path of its own; {path} is not."
        )
    if not folder.is_dir():
        raise CredentialsFileError(
            f"The folder {folder} does not exist. Mount the server's secrets folder there (see the runbook)."
        )
    if os.path.realpath(folder) != os.path.abspath(folder):
        raise CredentialsFileError(f"The folder {folder} is reached through a symbolic link; give its real path.")
    if not _is_mount(folder):
        raise CredentialsFileError(
            f"{folder} is not a mounted folder, so a file written there would vanish with this container. "
            "Mount the server's secrets folder there (see the runbook)."
        )


def _check_path(path: Path) -> None:
    require_credentials_location(path)
    if path.is_symlink():
        raise CredentialsFileError(f"{path} is a symbolic link; refusing to write a password through it.")


@contextmanager
def _open_folder() -> Iterator[int]:
    """A descriptor for the checked folder: every step below works relative to it."""
    try:
        descriptor = os.open(CREDENTIALS_DIR, os.O_RDONLY | os.O_DIRECTORY)
    except OSError as exc:
        raise CredentialsFileError(f"Could not open {CREDENTIALS_DIR}: {exc.strerror}.") from exc
    try:
        yield descriptor
    finally:
        os.close(descriptor)


def _open_file_in_folder(folder: int, path: Path) -> tuple[int, bool]:
    """Open the file by name inside the folder. Returns the descriptor and whether it was created."""
    name = path.name
    # O_NOFOLLOW refuses a symbolic link in place of the file itself; opening relative to the folder
    # means no directory component of the name is resolved at all.
    flags = os.O_RDWR | os.O_APPEND | os.O_NOFOLLOW
    # Creation is exclusive, so a file that already exists, even an empty one, is never taken for
    # one this run created.
    try:
        return os.open(name, flags | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=folder), True
    except FileExistsError:
        pass
    except OSError as exc:
        raise CredentialsFileError(f"Could not create {path}: {exc.strerror}.") from exc

    # O_NONBLOCK stops a FIFO from hanging the open.
    try:
        descriptor = os.open(name, flags | os.O_NONBLOCK, dir_fd=folder)
    except OSError as exc:
        raise CredentialsFileError(f"Could not open {path}: {exc.strerror}.") from exc
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise CredentialsFileError(f"{path} is not a regular file.")
        if info.st_nlink != 1:
            raise CredentialsFileError(f"{path} has another name (a hard link); refusing to write a password to it.")
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor, False


def _write_all(descriptor: int, data: bytes) -> None:
    written = 0
    while written < len(data):
        written += _write(descriptor, data[written:])


def _fsync_directory(folder: int) -> None:
    """Make a new file's name durable: flushing the file alone does not cover its directory entry."""
    _fsync(folder)


def _remove_new_file(descriptor: int, folder: int, path: Path) -> bool:
    """Remove a file this run created, if its name still refers to it. True if it was removed."""
    try:
        ours, there = os.fstat(descriptor), os.lstat(path.name, dir_fd=folder)
        if (ours.st_dev, ours.st_ino) != (there.st_dev, there.st_ino):
            return False
        os.unlink(path.name, dir_fd=folder)
    except OSError:
        return False
    return True


def _start_new_file(descriptor: int, folder: int, path: Path) -> None:
    """Write the header to a file this run created, and make the file and its name durable.

    Done before any password is written, so the database is never committed while the file could
    still vanish in a power cut. If it fails, the new file is removed again.
    """
    try:
        _write_all(descriptor, CREDENTIALS_FILE_HEADER.encode("utf-8"))
        _fsync(descriptor)
        _fsync_directory(folder)
    except OSError as exc:
        leftover = "" if _remove_new_file(descriptor, folder, path) else f" Remove the partly written {path} by hand."
        raise CredentialsFileError(f"Could not write to {path}: {exc.strerror}.{leftover}") from exc


def _require_signature(descriptor: int, path: Path) -> None:
    signature = CREDENTIALS_FILE_SIGNATURE.encode("utf-8")
    if os.pread(descriptor, len(signature), 0) != signature:
        raise CredentialsFileError(f"{path} was not created by this tool; refusing to add a password to it.")


def _require_complete_last_line(descriptor: int, path: Path) -> None:
    """Refuse a file whose last line was cut off, because appending would continue that line.

    Every line this tool writes ends in a newline, so a file that does not was written only part
    way - by a run that was killed, or by one whose note could not be cut back. A password
    appended after an unterminated comment line would be read as part of that comment, so the
    file is refused until someone removes the incomplete line.

    Removing it is always safe. A password line is written and flushed in full before anything is
    committed, so one left part way belongs to a run that saved nothing; and a part-written note
    sits after a password line that is complete.
    """
    size = os.fstat(descriptor).st_size
    if size and os.pread(descriptor, 1, size - 1) != b"\n":
        raise CredentialsFileError(
            f"{path} ends in an incomplete line, so it was not written in full. Remove that "
            "incomplete last line by hand - it is an unfinished note, or a password line from a "
            "run that saved nothing, never a password an account has - then run the command again."
        )


def _cut_back(descriptor: int, length: int, path: Path, username: str) -> None:
    try:
        _ftruncate(descriptor, length)
        _fsync(descriptor)
    except OSError as exc:
        raise CredentialsFileError(
            f"The change was not saved, and the new line for {username} could not be removed from "
            f"{path} ({exc.strerror}). Delete that line by hand: it is not a valid password."
        ) from exc


class PendingLine:
    """The credentials line just written: the caller removes it, or marks it, once it knows more."""

    def __init__(
        self, descriptor: int, keep_length: int, line_end: int, path: Path, username: str
    ) -> None:
        self._descriptor = descriptor
        self._keep_length = keep_length  # before the line: where removing it cuts back to
        self._line_end = line_end  # after it: where a note that failed part-way cuts back to
        self._path = path
        self._username = username

    def remove(self) -> None:
        """Cut the line back: the change is known not to have been saved."""
        _cut_back(self._descriptor, self._keep_length, self._path, self._username)

    def mark_unconfirmed(self) -> str:
        """Note in the file that the line may not have been saved, so a later reader sees it too.

        Returns MARK_WRITTEN, MARK_NOT_WRITTEN or MARK_INCOMPLETE, because the caller has to say
        which happened: claiming a mark the file does not hold would lose exactly the warning it
        exists to leave, and a note left half written ends the file mid-line.

        Which of the three it is comes from the file itself, never from which call failed. A write
        that fails before any byte reaches the file leaves the file whole, and cutting back a note
        that was never there cuts nothing back - so reading a failed cut-back as damage would tell
        the owner to remove the last line when that last line is the password, which may be the
        only copy of one the database has taken.
        """
        note = (
            f"{UNCONFIRMED_MARK} the line above, for {self._username}, may not have been saved; "
            "check by signing in with it. `list` says whether the account exists, never which "
            "password it has.\n"
        )
        try:
            _write_all(self._descriptor, note.encode("utf-8"))
            _fsync(self._descriptor)
        except BaseException:
            # Anything at all - a full disk, an I/O error, Ctrl+C - can leave part of the note in
            # the file, where it would end the file mid-line and the next run's password line would
            # continue that comment. Take back whatever arrived, then report what the file holds.
            # An interruption is not passed on: this command's message is the only certain record
            # of the doubt, and it still has to be printed.
            self._take_back_note()
            return self._state_after_a_failed_note()
        return MARK_WRITTEN

    def _take_back_note(self) -> None:
        """Cut a note that did not complete back to the end of the password line.

        Best effort only. Whether it worked is read from the file afterwards, not assumed from this
        returning: if the removal itself did not reach the disk, the next run's last-line check
        refuses the file rather than appending to a part line.
        """
        try:
            _ftruncate(self._descriptor, self._line_end)
            _fsync(self._descriptor)
        except BaseException:
            pass

    def _state_after_a_failed_note(self) -> str:
        """MARK_INCOMPLETE only if the file really ends mid-line; otherwise MARK_NOT_WRITTEN.

        Everything past the password line is note text, because that line was written and flushed
        in full before this. So the file ends mid-line only when note bytes are there without their
        newline - and then the incomplete last line is the note, never the password.
        """
        try:
            size = os.fstat(self._descriptor).st_size
            if size <= self._line_end:  # nothing of the note is in the file
                return MARK_NOT_WRITTEN
            ends_a_line = os.pread(self._descriptor, 1, size - 1) == b"\n"
        except BaseException:
            # The file cannot be read to tell. Report the outcome that asks for no repair by hand:
            # a file that does end mid-line is refused by the next password command, which says
            # what to remove, and this command's message already carries the doubt.
            return MARK_NOT_WRITTEN
        # A whole note that could not be taken back out is not damage. It may simply not have
        # reached the disk, which is what MARK_NOT_WRITTEN's message says.
        return MARK_NOT_WRITTEN if ends_a_line else MARK_INCOMPLETE


@contextmanager
def pending_credentials(path: Path, *, action: str, username: str, password: str) -> Iterator[PendingLine]:
    """Write one credentials line, which stays unless the body removes it.

    The line is on disk, flushed, before the body runs, and for a new file so is the file's name, so
    a password that reaches the database is never held only in memory. If writing it fails or is
    interrupted, it is cut back before anything is committed. After that it is removed only by the
    body, once the change is known not to have been saved: an exception or an interruption from the
    body leaves it in place, because a commit that did not return normally may still have taken
    effect. The file stays locked throughout, so two runs cannot interleave or undo each other's
    lines.

    Not covered: the process being killed between the write and the commit. The line may then name
    a password the account does not have - and for a killed `create` the account may not exist at
    all, so `reset-password` would have nothing to reset. The runbook settles it per command: for a
    `create`, `list` first, and run `create` again if the username is not there; for a
    `reset-password`, sign in with the kept line, or replace it with a `reset-password` run that
    reported success.
    """
    _check_path(path)
    with _open_folder() as folder:
        descriptor, created = _open_file_in_folder(folder, path)
        try:
            # A run that opens a file another run created a moment earlier, before that run has
            # written its header, refuses it; running it again works.
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            if created:
                _start_new_file(descriptor, folder, path)
            else:
                _require_signature(descriptor, path)
                _require_complete_last_line(descriptor, path)
            original_length = os.fstat(descriptor).st_size
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            data = f"{timestamp}\t{action}\t{username}\t{password}\n".encode("utf-8")
            try:
                # Also tightens a file that already existed with looser permissions.
                os.fchmod(descriptor, 0o600)
                _write_all(descriptor, data)
                _fsync(descriptor)
            except OSError as exc:
                _cut_back(descriptor, original_length, path, username)
                raise CredentialsFileError(f"Could not write to {path}: {exc.strerror}.") from exc
            except BaseException:
                # Interrupted while writing: nothing is committed yet, so the line goes.
                _cut_back(descriptor, original_length, path, username)
                raise
            line_end = os.fstat(descriptor).st_size
            yield PendingLine(descriptor, original_length, line_end, path, username)
        finally:
            os.close(descriptor)


def append_credentials(path: Path, *, action: str, username: str, password: str) -> None:
    """Append one line and keep it."""
    with pending_credentials(path, action=action, username=username, password=password):
        pass
