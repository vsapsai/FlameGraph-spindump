This project visualizes stack traces in hang and spin reports on Mac OS X.  It aims to solve the following problem: it's hard to pinpoint quickly a function where the most time is spent in a big stack trace.  Big means more than 2 screens long.

The project is **heavily** inspired by remarkable [brendangregg/FlameGraph](https://github.com/brendangregg/FlameGraph).  But I am implementing everything from scratch in Python, that's why I'm not forking the original project.  I'll see how can I contribute my work to Brendan's project.

## See Also
Most useful resources:

* [http://dtrace.org/blogs/brendan/2011/12/16/flame-graphs/](http://dtrace.org/blogs/brendan/2011/12/16/flame-graphs/)
* [https://github.com/brendangregg/FlameGraph](https://github.com/brendangregg/FlameGraph)
* `man spindump`
* `man sample`

Other useful resources:

* [http://schani.wordpress.com/2012/11/16/flame-graphs-for-instruments/](http://schani.wordpress.com/2012/11/16/flame-graphs-for-instruments/)
* [http://samsaffron.com/archive/2013/03/19/flame-graphs-in-ruby-miniprofiler](http://samsaffron.com/archive/2013/03/19/flame-graphs-in-ruby-miniprofiler)
* [http://randomascii.wordpress.com/2013/03/26/summarizing-xperf-cpu-usage-with-flame-graphs/](http://randomascii.wordpress.com/2013/03/26/summarizing-xperf-cpu-usage-with-flame-graphs/)
