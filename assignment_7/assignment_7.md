1. I started out by simply putting the sentances into the the embedding model and getting vectors, and then running a matrix multiplication on them to
find similarity. Just the stuff that we did in class.
2. Afterwards I started to mix similar sentances in english and spanish, as well as using names, to find how much specific words made a difference. It
turns out that names that are the same across lanugages can boost the dot product almost .1 similarity. I would use sentances like "my name is dora"
and "yo me llamo dora". that would generally get a similarity rating of about .5. Afterwards i would change the name to bob on one and leave the name
dora in the other. This would only get about .4.
3. I started to expiriment with large text files, containing about 300 lines of text. The model could handle it. interestingly It would get a higher similarity 
score when the sentance that we were trying to match were summarys of the text rather than sentences found within the text. This made me think of how a json could be used for searching.
you could have a parent search, trying to find similaritys to the document as a whole, or the title, whith a child search for reslutls once a document is found that has what you are looking for
that or you could have every sentance in a gigantic database and search thorugh all of them
4. the last and most interesting thing i did was i tryied to turn the whole bible into a single vector. It didn't work. There are only so many tokens that the two embedding models can handle.
So I opted for seperating the bible by sentances. trying to encode that would have taken forever, so i only did a thousand sentances.
 searching though thouse thousand sentances only took about .2 seconds, which makes me think that there are things that we coudl do to make it go faster
