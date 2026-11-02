-- Apple Music Organizer v2.
-- Inventory emits: name, persistent_id, full_path, media_kind, genre, artist, tracks.
-- Apply consumes: MOVE<TAB>persistent_id<TAB>destination.

on run argv
	if (count of argv) is 0 then error "Expected inventory or apply"
	if (item 1 of argv) is "inventory" then return inventoryText()
	if (item 1 of argv) is "apply" then
		if (count of argv) < 2 then error "Apply requires a reviewed plan file"
		return applyPlan(item 2 of argv)
	end if
	error "Unknown mode: " & (item 1 of argv)
end run

on inventoryText()
	tell application "Music"
		set outLines to {}
		set allPlaylists to every user playlist
		set specialKinds to special kind of every user playlist
		repeat with i from 1 to (count of allPlaylists)
			set p to item i of allPlaylists
			set isPlain to false
			set pName to ""
			set pID to ""
			set pathText to ""
			try
				set isPlain to ((item i of specialKinds as text) is "none")
				if isPlain then
					set pName to my clean(name of p)
					set pID to persistent ID of p
					set pathText to my pathOfParent(p)
				end if
			on error
				set isPlain to false
			end try
			if isPlain then
				set trackCount to 0
				set genreText to ""
				set artistText to ""
				set trackText to ""
				try
					set trackCount to count of tracks of p
					if trackCount > 0 then
						set sampleEnd to trackCount
						if sampleEnd > 12 then set sampleEnd to 12
						set trackText to my joinText(name of tracks 1 thru sampleEnd of p, " | ")
						set genreText to my joinText(genre of tracks 1 thru sampleEnd of p, ", ")
						set artistText to my joinText(artist of tracks 1 thru sampleEnd of p, ", ")
					end if
				end try
				set end of outLines to pName & tab & pID & tab & pathText & tab & "user playlist" & tab & trackCount & tab & my clean(genreText) & tab & my clean(artistText) & tab & my clean(trackText)
			end if
		end repeat
	end tell
	return my joinText(outLines, linefeed)
end inventoryText

-- Folder path of an item's parent chain, using the "parent" property (container is always Library).
on pathOfParent(theItem)
	set parts to {}
	tell application "Music"
		set currentItem to theItem
		repeat 20 times
			try
				set currentItem to parent of currentItem
				set beginning of parts to name of currentItem
			on error
				exit repeat
			end try
		end repeat
	end tell
	return my joinText(parts, "/")
end pathOfParent

on joinText(theList, theDelimiter)
	set oldDelims to AppleScript's text item delimiters
	set AppleScript's text item delimiters to theDelimiter
	set resultText to (theList as text)
	set AppleScript's text item delimiters to oldDelims
	return resultText
end joinText

on clean(theText)
	set theText to theText as text
	set oldDelims to AppleScript's text item delimiters
	repeat with ch in {tab, linefeed, return}
		set AppleScript's text item delimiters to ch
		set pieces to text items of theText
		set AppleScript's text item delimiters to " "
		set theText to pieces as text
	end repeat
	set AppleScript's text item delimiters to oldDelims
	return theText
end clean

-- Returns {paths, refs} for every folder; the first folder seen for a path is the one reused.
on folderIndex()
	set paths to {}
	set refs to {}
	tell application "Music"
		repeat with f in (every folder playlist)
			set folderRef to contents of f
			set folderPath to my pathOfParent(folderRef)
			if folderPath is "" then
				set folderPath to name of folderRef
			else
				set folderPath to folderPath & "/" & (name of folderRef)
			end if
			if folderPath is not in paths then
				set end of paths to folderPath
				set end of refs to persistent ID of folderRef
			end if
		end repeat
	end tell
	return {paths, refs}
end folderIndex

on applyPlan(planPath)
	set planText to read (POSIX file planPath) as «class utf8»
	set folderData to my folderIndex()
	set knownPaths to item 1 of folderData
	set knownRefs to item 2 of folderData
	set moved to 0
	repeat with lineRef in paragraphs of planText
		set lineText to lineRef as text
		if lineText starts with "MOVE" & tab then
			set parts to my splitText(lineText, tab)
			if (count of parts) is not 3 then error "Invalid apply record: " & lineText
			set playlistID to item 2 of parts
			set destination to item 3 of parts
			set folderID to my ensurePath(destination, knownPaths, knownRefs)
			tell application "Music"
				set folderRef to first folder playlist whose persistent ID is folderID
				set matches to (every user playlist whose persistent ID is playlistID)
				if (count of matches) is not 1 then error "Refusing identity " & playlistID & ": expected one match"
				move (item 1 of matches) to folderRef
			end tell
			set moved to moved + 1
		end if
	end repeat
	return "Applied " & moved
end applyPlan

-- Walks the path, reusing existing folders and creating only the missing segments.
on ensurePath(destination, knownPaths, knownRefs)
	set segments to my splitText(destination, "/")
	set currentPath to ""
	set parentRef to missing value
	repeat with seg in segments
		set segName to seg as text
		if currentPath is "" then
			set currentPath to segName
		else
			set currentPath to currentPath & "/" & segName
		end if
		set pos to 0
		repeat with i from 1 to (count of knownPaths)
			if (item i of knownPaths) is currentPath then
				set pos to i
				exit repeat
			end if
		end repeat
		if pos > 0 then
			set parentRef to item pos of knownRefs
		else
			tell application "Music"
				if parentRef is missing value then
					set newRef to make new folder playlist with properties {name:segName}
				else
					set parentFolder to first folder playlist whose persistent ID is parentRef
					set newRef to make new folder playlist at parentFolder with properties {name:segName}
				end if
				set newID to persistent ID of newRef
			end tell
			set end of knownPaths to currentPath
			set end of knownRefs to newID
			set parentRef to newID
		end if
	end repeat
	return parentRef
end ensurePath

on splitText(theText, theDelimiter)
	set oldDelims to AppleScript's text item delimiters
	set AppleScript's text item delimiters to theDelimiter
	set resultItems to text items of theText
	set AppleScript's text item delimiters to oldDelims
	return resultItems
end splitText
