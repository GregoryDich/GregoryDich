#pragma once

/**
 * Incremental Server-Sent Events parser (contract §2, `GET /v1/jobs/{id}/events`).
 *
 * Standard-library only so it can be unit-tested without JUCE. Bytes are fed as they
 * arrive from the socket; complete events are returned in order. Handles CRLF / LF / CR
 * line endings, partial chunks, multi-line `data:` fields (joined with '\n'), comment
 * lines such as `: ping`, and a leading UTF-8 BOM. `id:` and `retry:` are ignored.
 */

#include <cstddef>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace tonamorph::cloud::sse
{

struct Event
{
    std::string name;   ///< the `event:` field, "message" when the stream did not name it
    std::string data;   ///< all `data:` lines joined with '\n'
};

class Parser
{
public:
    /** Feeds raw bytes and returns every event completed by them. */
    std::vector<Event> feed (const char* bytes, std::size_t numBytes)
    {
        std::vector<Event> completed;

        for (std::size_t i = 0; i < numBytes; ++i)
        {
            const char c = bytes[i];

            if (c == '\n' && lastWasCarriageReturn)
            {
                lastWasCarriageReturn = false;   // second half of a CRLF pair
                continue;
            }

            lastWasCarriageReturn = (c == '\r');

            if (c == '\r' || c == '\n')
            {
                processLine (pendingLine, completed);
                pendingLine.clear();
            }
            else
            {
                pendingLine.push_back (c);
            }
        }

        return completed;
    }

    /** Flushes an event whose terminating blank line never arrived (stream closed). */
    std::optional<Event> finish()
    {
        std::vector<Event> completed;

        if (! pendingLine.empty())
        {
            processLine (pendingLine, completed);
            pendingLine.clear();
        }

        if (completed.empty())
            dispatch (completed);

        lastWasCarriageReturn = false;

        if (completed.empty())
            return std::nullopt;

        return completed.front();
    }

    /** The `event:` name of the event currently being assembled (empty if none yet). */
    const std::string& getCurrentEventName() const noexcept { return eventName; }

private:
    void processLine (std::string_view line, std::vector<Event>& completed)
    {
        if (atStreamStart)
        {
            atStreamStart = false;

            if (line.size() >= 3 && static_cast<unsigned char> (line[0]) == 0xEF
                && static_cast<unsigned char> (line[1]) == 0xBB && static_cast<unsigned char> (line[2]) == 0xBF)
                line.remove_prefix (3);
        }

        if (line.empty())
        {
            dispatch (completed);
            return;
        }

        if (line.front() == ':')
            return;   // comment / heartbeat

        const auto colon = line.find (':');
        const auto field = line.substr (0, colon);
        auto value = colon == std::string_view::npos ? std::string_view() : line.substr (colon + 1);

        if (! value.empty() && value.front() == ' ')
            value.remove_prefix (1);

        if (field == "event")
        {
            eventName.assign (value);
        }
        else if (field == "data")
        {
            data.append (value);
            data.push_back ('\n');
            hasData = true;
        }
    }

    void dispatch (std::vector<Event>& completed)
    {
        if (hasData)
        {
            if (! data.empty() && data.back() == '\n')
                data.pop_back();

            completed.push_back ({ eventName.empty() ? std::string ("message") : eventName, data });
        }

        eventName.clear();
        data.clear();
        hasData = false;
    }

    std::string pendingLine;
    std::string eventName;
    std::string data;
    bool hasData = false;
    bool lastWasCarriageReturn = false;
    bool atStreamStart = true;
};

} // namespace tonamorph::cloud::sse
