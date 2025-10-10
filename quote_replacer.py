import sublime
import sublime_plugin
import re


class SmartQuoteReplacerCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        # Get the entire content or selected text
        # Check if there's a selection by looking at the selection regions
        sel = self.view.sel()
        if len(sel) == 1 and sel[0].empty():
            # No selection, process entire document
            regions = [sublime.Region(0, self.view.size())]
        else:
            # There is a selection, process only selected regions
            regions = list(sel)

        for region in regions:
            text = self.view.substr(region)
            new_text = self.replace_quotes_preserve_html_and_css(text)
            if new_text != text:
                self.view.replace(edit, region, new_text)

    def replace_quotes_preserve_html_and_css(self, text):
        # First, protect style and script blocks by temporarily replacing them
        style_blocks = []
        script_blocks = []

        # Extract and store style blocks
        def store_style(match):
            style_blocks.append(match.group(0))
            return f"__STYLE_BLOCK_{len(style_blocks)-1}__"

        def store_script(match):
            script_blocks.append(match.group(0))
            return f"__SCRIPT_BLOCK_{len(script_blocks)-1}__"

        # Temporarily replace style and script blocks
        text = re.sub(
            r"<style[^>]*>.*?</style>",
            store_style,
            text,
            flags=re.DOTALL | re.IGNORECASE,
        )
        text = re.sub(
            r"<script[^>]*>.*?</script>",
            store_script,
            text,
            flags=re.DOTALL | re.IGNORECASE,
        )

        # First, convert any existing smart quotes (curly quotes) to HTML entities
        text = self.convert_smart_quotes_to_entities(text)

        # Now process straight quotes while preserving HTML tags
        text = self.replace_quotes_smart(text)

        # Restore style blocks
        for i, style_block in enumerate(style_blocks):
            text = text.replace(f"__STYLE_BLOCK_{i}__", style_block)

        # Restore script blocks
        for i, script_block in enumerate(script_blocks):
            text = text.replace(f"__SCRIPT_BLOCK_{i}__", script_block)

        return text

    def convert_smart_quotes_to_entities(self, text):
        """Convert existing curly/smart quotes to HTML entities outside of HTML tags"""
        result = []
        i = 0

        while i < len(text):
            if text[i] == "<":
                # Start of HTML tag, find the end
                tag_end = text.find(">", i)
                if tag_end != -1:
                    # Include the entire tag without modification
                    result.append(text[i : tag_end + 1])
                    i = tag_end + 1
                else:
                    result.append(text[i])
                    i += 1
            elif text[i] == '“':  # Left double quote
                result.append("&ldquo;")
                i += 1
            elif text[i] == '”':  # Right double quote
                result.append("&rdquo;")
                i += 1
            elif text[i] == '‘':  # Left single quote
                result.append('&lsquo;')
                i += 1
            elif text[i] == '’':  # Right single quote
                result.append("&rsquo;")
                i += 1
            else:
                result.append(text[i])
                i += 1

        return "".join(result)

    def replace_quotes_smart(self, text):
        # Handle apostrophes first (before quote processing)

        # Graduation years (apostrophe before 2 digits)
        text = re.sub(r"'(\d{2})(?=\W|$)", r"&rsquo;\1", text)

        # Contractions (apostrophes in middle of words)
        text = re.sub(r"(\w)'(\w)", r"\1&rsquo;\2", text)

        # Possessives (apostrophes at end of words)
        text = re.sub(r"(\w)'(s\b|\s|$|[^\w])", r"\1&rsquo;\2", text)

        # Now handle quotes with HTML awareness
        # This approach tracks quote state while skipping over HTML tags

        # Handle double quotes
        text = self.replace_double_quotes_html_aware(text)

        # Handle single quotes (that aren't apostrophes)
        text = self.replace_single_quotes_html_aware(text)

        return text

    def replace_double_quotes_html_aware(self, text):
        result = []
        in_quote = False
        i = 0

        while i < len(text):
            if text[i] == '"':
                # Check if we're inside an HTML tag by looking backwards and forwards
                if self.is_inside_html_tag(text, i):
                    # We're inside an HTML tag, don't replace
                    result.append(text[i])
                else:
                    # We're in text content, replace the quote
                    if in_quote:
                        result.append("&rdquo;")
                        in_quote = False
                    else:
                        result.append("&ldquo;")
                        in_quote = True
                i += 1
            elif text[i] == "<":
                # Start of HTML tag, find the end
                tag_end = text.find(">", i)
                if tag_end != -1:
                    # Include the entire tag
                    result.append(text[i : tag_end + 1])
                    i = tag_end + 1
                else:
                    result.append(text[i])
                    i += 1
            else:
                result.append(text[i])
                i += 1

        return "".join(result)

    def replace_single_quotes_html_aware(self, text):
        # For single quotes, we need to be more careful since they're often apostrophes
        # Only replace quotes that look like actual quotation marks

        # Opening single quote: after whitespace, punctuation, or start of string/line
        text = re.sub(r"(^|\s|[(\[{—-])'(?=\w)", r"\1&lsquo;", text)

        # Closing single quote: after word characters, before whitespace/punctuation/end
        # But avoid replacing if we're inside an HTML tag
        def replace_closing_quote(match):
            full_match = match.group(0)
            before = match.group(1)

            # Simple check: if the quote is followed by common HTML attribute patterns, skip it
            remaining_text = text[match.end() :]
            if re.match(r"\s*[=>]", remaining_text):
                return full_match  # Likely inside HTML, don't replace

            return before + "&rsquo;"

        text = re.sub(r"(\w)'(?=\s|[.,;:!?)}\]—-]|$)", replace_closing_quote, text)

        return text

    def is_inside_html_tag(self, text, pos):
        # Look backwards for the most recent < or >
        last_open = text.rfind("<", 0, pos)
        last_close = text.rfind(">", 0, pos)

        # If we found a < more recently than >, we're inside a tag
        return last_open > last_close


class SmartQuoteReplacerListener(sublime_plugin.EventListener):
    def on_modified_async(self, view):
        # Optional: Auto-replace as you type
        # Uncomment the following lines if you want real-time replacement
        pass
        # settings = view.settings()
        # if settings.get('smart_quote_auto_replace', False):
        #     view.run_command('smart_quote_replacer')
