## Python Concurrency Q&A

Or: Python is a Good Language for Concurrency.

---

## Concurrency vs Parallelism

* Concurrency - interleaving tasks to avoid waiting. (usually IO Bound)
* Parallelism - doing large computations in parallel. (usually CPU Bound)

---

## The Global Interpreter Lock (GIL)

* Only one python VM instruction can be run at a time.
* Simple implementation that keeps single threaded python fast.
* I don't care about the GIL!

---

## Tools for Parallelism

* Multiprocessing (run code in separate processeses / python VMs)
* C extensions that release the GIL while they do work.
* Use the GPU!

---

## Threads

* Provided by the operating system.
* No control over context switching.
* High performance overhead. (Don't use too many!)

---

## Async IO

* Co-operative multitasking.
* Explicit control over context switching.
* Syntax support in Python 3.5+
* Probably the future of the language.

---

Content Warning: Opinions

---

* Unnecessarily complex and confusing.
* Requires rewriting huge portions of your application...
* ...forking all the libraries.
* Gives you all the wrong foot-guns.
* All the "joy" of concurrent programming in Javascript or Rust.

---

## Green Threads

* eventlet or gevent.
* Co-operative multitasking with implicit context switching.
* Monkey patching magic!
* Some of the joy of concurrent programming in Erlang, Elixir or Golang.

What about threading bugs?

---

## Communicating Sequential Processes

* Communicate by passing messages. (Queue.Queue, eventlet.Queue or asyncio.Queue)
* Built in datastructures are thread safe. (dicts, lists, sets, etc.)
* Be careful with exceptions!
