-- Preview-first merger for duplicate Apple Music folders under a root folder.
-- Usage:
--   osascript MergeAppleMusicFolders.applescript preview "AI Organized"
--   osascript MergeAppleMusicFolders.applescript apply   "AI Organized"
-- Same-path folders are merged into the first one seen; only folders left empty are deleted.
-- Children are found through each item's "parent" property (Music cannot filter by parent).

on run argv
	if (count of argv) < 1 then error "Usage: preview|apply [root folder name]"
	set modeName to item 1 of argv
	set rootName to "AI Organized"
	if (count of argv) ≥ 2 then set rootName to item 2 of argv
	if modeName is not "preview" and modeName is not "apply" then error "Mode must be preview or apply."
	set totalMoves to 0
	set totalDeleted to 0
	repeat 12 times
		set stats to my mergePass(rootName, modeName is "apply")
		set totalMoves to totalMoves + (item 1 of stats)
		set totalDeleted to totalDeleted + (item 2 of stats)
		if modeName is "preview" or ((item 1 of stats) + (item 2 of stats)) is 0 then exit repeat
	end repeat
	return modeName & ": " & totalMoves & " items moved, " & totalDeleted & " empty duplicate folders deleted/deletable"
end run

on pathOf(theItem)
	set parts to {}
	tell application "Music"
		set currentItem to theItem
		set end of parts to name of currentItem
		repeat 20 times
			try
				set currentItem to parent of currentItem
				set beginning of parts to name of currentItem
			on error
				exit repeat
			end try
		end repeat
	end tell
	set oldDelims to AppleScript's text item delimiters
	set AppleScript's text item delimiters to "/"
	set resultText to parts as text
	set AppleScript's text item delimiters to oldDelims
	return resultText
end pathOf

on mergePass(rootName, doApply)
	set movedCount to 0
	set deletedCount to 0
	-- One pass over all items: remember path, id and parent id so later steps need no extra Music calls.
	set folderRefs to {}
	set folderPaths to {}
	set folderIDs to {}
	set folderParentIDs to {}
	set itemRefs to {}
	set itemParentIDs to {}
	tell application "Music"
		set allFolders to every folder playlist
		set allPlaylists to every user playlist
	end tell
	repeat with f in allFolders
		try
			set folderRef to contents of f
			set fid to ""
			tell application "Music" to set fid to persistent ID of folderRef
			set end of folderPaths to my pathOf(folderRef)
			set end of folderIDs to fid
			set end of folderParentIDs to my parentIDOf(folderRef)
			set end of folderRefs to folderRef
		end try
	end repeat
	repeat with p in allPlaylists
		try
			set pRef to contents of p
			set end of itemParentIDs to my parentIDOf(pRef)
			set end of itemRefs to pRef
		end try
	end repeat
	set canonPaths to {}
	set canonRefs to {}
	set dupIdx to {}
	repeat with i from 1 to (count of folderRefs)
		set fp to item i of folderPaths
		if fp is rootName or fp starts with (rootName & "/") then
			if fp is in canonPaths then
				set end of dupIdx to i
			else
				set end of canonPaths to fp
				set end of canonRefs to item i of folderRefs
			end if
		end if
	end repeat
	repeat with i in dupIdx
		set dupID to item i of folderIDs
		set targetRef to missing value
		repeat with k from 1 to (count of canonPaths)
			if (item k of canonPaths) is (item i of folderPaths) then set targetRef to item k of canonRefs
		end repeat
		set childRefs to {}
		repeat with j from 1 to (count of folderRefs)
			if (item j of folderParentIDs) is dupID then set end of childRefs to item j of folderRefs
		end repeat
		repeat with j from 1 to (count of itemRefs)
			if (item j of itemParentIDs) is dupID then set end of childRefs to item j of itemRefs
		end repeat
		repeat with childRef in childRefs
			set movedCount to movedCount + 1
			if doApply then tell application "Music" to move (contents of childRef) to targetRef
		end repeat
		if (count of childRefs) is 0 then
			set deletedCount to deletedCount + 1
			if doApply then tell application "Music" to delete (item i of folderRefs)
		end if
	end repeat
	return {movedCount, deletedCount}
end mergePass

on parentIDOf(theItem)
	tell application "Music"
		try
			return persistent ID of (parent of theItem)
		on error
			return ""
		end try
	end tell
end parentIDOf
