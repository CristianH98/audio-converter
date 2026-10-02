# Review rules

Claude reviews every pull request and sorts each issue it finds as
**severe** or **minor**. Any severe issue fails the `review` check and
blocks the merge. Minor issues never block.

The review workflow always reads this file from `main`, so a pull request
cannot change the rules it is reviewed against. Changes to this file take
effect once they are merged.

## Scope

Only problems that the pull request introduces, or code it changes, can be
severe. Problems in code the pull request does not touch are minor at most.

When unsure whether something is severe, treat it as minor.

## Severe

1. **Wrong result.** The wrong input file is picked, the output is written
   to the wrong place or with the wrong name, or the ffmpeg arguments are
   wrong for the output format.
2. **Data loss.** Deleting files, or overwriting anything other than the
   output file in `audio/`. Overwriting that output file is intended.
3. **Crash in normal use.** A raw traceback instead of a clean error message
   for common situations: a missing input file, a non-video file, a missing
   `ffmpeg`/`ffprobe`, or ffmpeg failing. Errors meant for the user go
   through `ConversionError`.
4. **Security.** `shell=True` or commands built from strings with user
   input, or writing outside `audio/` through crafted file names.
5. **Breaking the CLI.** Removing or renaming flags, or changing defaults or
   exit codes, unless the pull request says the change is intended.
6. **Broken tests or CI.** Failing tests, or tests that need real ffmpeg or
   media files, or that write into the repository's `video/` or `audio/`
   folders.
7. **Committed secrets.** Tokens, keys or credentials in the code.

## Minor

- Missing tests for new or changed behavior.
- Naming, readability, comments and docs.
- Refactoring ideas and small simplifications.
- Performance, unless it makes the tool unusable.

## Review format

Write like a teammate leaving a quick note: casual, direct, no filler.
Aim for under 100 words. The reader has the diff open, so don't explain
what the code does.

Use exactly these sections:

- `### Severe`: one bullet per issue, `file:line` plus the problem and the
  fix in one short sentence. Add a code snippet only when the fix isn't
  obvious, 5 lines max. Write "None 🎉" if there are none.
- `### Minor`: at most 5 one-line bullets, most useful first. Skip
  nitpicks. Write "None" if there are none.

End with one line: `**Verdict:** ✅ Good to merge` if there are no
severe issues, otherwise `**Verdict:** ❌ Needs changes`.
