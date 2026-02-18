# what i learned
 - tool calling allows for your agent to preform autonomus task
 - Controling the system prompt allows for how you want your agent to make the tool calls
 - one of the interesting things that i learned was that there was not the bot would frequently choose to not use tools for smiple arithmatic and would instead opt for just doing things like multiplication internally.
# What I did
 - I created a few differnt fucitons that interact together, the first gets the speakers url from their name
 - Afterward the url scrape all of the conference talks for the speaker, and then return them as a list. I opted to not append all of the talks to context, becuase it would be expensive, but instead opted for a proof of concept where it would append and search the most recient talk. If I were creating a real app, I would vectorize each of the paragraphs and store them in a rag database.
 - I created some **stats** tools that are the bot could use. but for super simple things like counting the number of char's in a string, or the absolute value function, it decided to just do it itself.