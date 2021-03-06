#!/usr/bin/env python
# Copyright (C) 2010 Google Inc. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Compares the text output of a test to the expected text output.

If the output doesn't match, returns FailureTextMismatch and outputs the diff
files into the layout test results directory.
"""

from __future__ import with_statement

import codecs
import errno
import logging
import os.path

from webkitpy.layout_tests.layout_package import test_failures
from webkitpy.layout_tests.test_types import test_type_base

_log = logging.getLogger("webkitpy.layout_tests.test_types.text_diff")


class TestTextDiff(test_type_base.TestTypeBase):

    def get_normalized_output_text(self, output):
        # Some tests produce "\r\n" explicitly.  Our system (Python/Cygwin)
        # helpfully changes the "\n" to "\r\n", resulting in "\r\r\n".
        norm = output.replace("\r\r\n", "\r\n").strip("\r\n").replace(
             "\r\n", "\n")
        return norm + "\n"

    def get_normalized_expected_text(self, filename, show_sources):
        """Given the filename of the test, read the expected output from a file
        and normalize the text.  Returns a string with the expected text, or ''
        if the expected output file was not found."""
        # Read the port-specific expected text.
        expected_filename = self._port.expected_filename(filename, '.txt')
        if show_sources:
            _log.debug('Using %s' % expected_filename)

        return self.get_normalized_text(expected_filename)

    def get_normalized_text(self, filename):
        # FIXME: We repeat this pattern often, we should share code.
        try:
            # NOTE: -expected.txt files are ALWAYS utf-8.  However,
            # we do not decode the output from DRT, so we should not
            # decode the -expected.txt values either to allow comparisons.
            with codecs.open(filename, "r", encoding=None) as file:
                text = file.read()
                # We could assert that the text is valid utf-8.
        except IOError, e:
            if errno.ENOENT != e.errno:
                raise
            return ''

        # Normalize line endings
        return text.strip("\r\n").replace("\r\n", "\n") + "\n"

    def compare_output(self, port, filename, output, test_args, configuration):
        """Implementation of CompareOutput that checks the output text against
        the expected text from the LayoutTest directory."""
        failures = []

        # If we're generating a new baseline, we pass.
        if test_args.new_baseline:
            # Although all test_shell/DumpRenderTree output should be utf-8,
            # we do not ever decode it inside run-webkit-tests.  For some tests
            # DumpRenderTree may not output utf-8 text (e.g. webarchives).
            self._save_baseline_data(filename, output, ".txt", encoding=None)
            return failures

        # Normalize text to diff
        output = self.get_normalized_output_text(output)
        expected = self.get_normalized_expected_text(filename,
                                                     test_args.show_sources)

        # Write output files for new tests, too.
        if port.compare_text(output, expected):
            # Text doesn't match, write output files.
            self.write_output_files(port, filename, ".txt", output,
                                    expected, encoding=None,
                                    print_text_diffs=True)

            if expected == '':
                failures.append(test_failures.FailureMissingResult(self))
            else:
                failures.append(test_failures.FailureTextMismatch(self, True))

        return failures

    def diff_files(self, port, file1, file2):
        """Diff two text files.

        Args:
          file1, file2: full paths of the files to compare.

        Returns:
          True if two files are different.
          False otherwise.
        """

        return port.compare_text(self.get_normalized_text(file1),
                                     self.get_normalized_text(file2))
