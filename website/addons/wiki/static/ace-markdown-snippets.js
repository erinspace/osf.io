ace.define("ace/snippets/markdown",["require","exports","module"], function(require, exports, module) {
"use strict";

exports.snippetText = "# Markdown\n\
\n\
snippet font-italic\n\
	*${1:text}*\n\
\n\
snippet font-bold\n\
	**${1:text}**\n\
\n\
snippet heading-1\n\
	# ${1:title}\n\
\n\
snippet heading-2\n\
	## ${1:title}\n\
\n\
snippet heading-3\n\
	### ${1:title}\n\
\n\
snippet heading-4\n\
	#### ${1:title}\n\
\n\
snippet horizontal-rule\n\
	\n\
	---\n\
	\n\
\n\
snippet blockquote\n\
	> ${1:quote}\n\
\n\
snippet codeblock\n\
	```\n\
	${1:snippet}\n\
	```\n\
\n\
snippet ![ (image)\n\
snippet image\n\
	![${1:alttext}](${2:url} \"${3:title}\")\n\
\n\
snippet [ (hyperlink)\n\
snippet hyperlink\n\
	[${1:linktext}](${2:url} \"${3:title}\")\n\
\n\
snippet numbered-list\n\
	1. ${1:item}\n\
\n\
snippet bulleted-list\n\
	* ${1:item}\n\
\n\
";
exports.scope = "markdown";

});
