// Rust 完整教程 - 第7章
// 
// 涵盖内容：
// - 基础语法
// - 所有权系统
// - 结构体和枚举
// - 泛型
// - 特征
// - 错误处理
// - 模块系统
// - 并发编程

// ============================================
// 第1节：基础语法
// ============================================

// Hello World
fn main() {
    println!("Hello, World!");
}

// 变量
fn variables() {
    // 不可变变量（默认）
    let x = 5;
    // x = 6; // 错误！
    println!("The value of x is: {}", x);
    
    // 可变变量
    let mut y = 5;
    println!("The value of y is: {}", y);
    y = 6;
    println!("The value of y is: {}", y);
    
    // 常量
    const MAX_POINTS: u32 = 100_000;
    println!("Max points: {}", MAX_POINTS);
    
    // 变量遮蔽
    let spaces = "   ";
    let spaces = spaces.len();
    println!("Spaces length: {}", spaces);
}

// 数据类型
fn data_types() {
    // 整数类型
    let a: i8 = -128;
    let b: u8 = 255;
    let c: i16 = -32768;
    let d: u16 = 65535;
    let e: i32 = -2147483648;
    let f: u32 = 4294967295;
    let g: i64 = -9223372036854775808;
    let h: u64 = 18446744073709551615;
    let i: isize = -9223372036854775808; // 根据架构
    let j: usize = 18446744073709551615; // 根据架构
    
    // 浮点数
    let x = 2.0; // f64
    let y: f32 = 3.0; // f32
    
    // 布尔值
    let t = true;
    let f: bool = false;
    
    // 字符
    let c = 'z';
    let z = 'ℤ';
    let heart_eyed_cat = '😻';
    
    // 元组
    let tup: (i32, f64, u8) = (500, 6.4, 1);
    let (x, y, z) = tup;
    println!("The value of y is: {}", y);
    let five_hundred = tup.0;
    let six_point_four = tup.1;
    let one = tup.2;
    
    // 数组
    let arr = [1, 2, 3, 4, 5];
    let first = arr[0];
    let second = arr[1];
    
    // 数组类型
    let arr2: [i32; 5] = [1, 2, 3, 4, 5];
    let arr3 = [3; 5]; // [3, 3, 3, 3, 3]
}

// 函数
fn functions() {
    // 基本函数
    fn another_function(x: i32, y: i32) {
        println!("The value of x is: {}", x);
        println!("The value of y is: {}", y);
    }
    
    another_function(5, 6);
    
    // 有返回值的函数
    fn five() -> i32 {
        5
    }
    
    fn plus_one(x: i32) -> i32 {
        x + 1
    }
    
    let x = five();
    let y = plus_one(5);
    println!("x: {}, y: {}", x, y);
}

// 控制流
fn control_flow() {
    // if 表达式
    let number = 6;
    
    if number % 4 == 0 {
        println!("number is divisible by 4");
    } else if number % 3 == 0 {
        println!("number is divisible by 3");
    } else if number % 2 == 0 {
        println!("number is divisible by 2");
    } else {
        println!("number is not divisible by 4, 3, or 2");
    }
    
    // if 是表达式
    let condition = true;
    let number = if condition { 5 } else { 6 };
    println!("The value of number is: {}", number);
    
    // 循环 - loop
    let mut counter = 0;
    let result = loop {
        counter += 1;
        if counter == 10 {
            break counter * 2;
        }
    };
    println!("The result is {}", result);
    
    // 循环 - while
    let mut number = 3;
    while number != 0 {
        println!("{}!", number);
        number -= 1;
    }
    println!("LIFTOFF!!!");
    
    // 循环 - for
    let a = [10, 20, 30, 40, 50];
    for element in a.iter() {
        println!("the value is: {}", element);
    }
    
    for number in (1..4).rev() {
        println!("{}!", number);
    }
    println!("LIFTOFF!!!");
}

// ============================================
// 第2节：所有权系统
// ============================================

fn ownership() {
    // 所有权规则
    // 1. Rust 中的每一个值都有一个变量，称为其所有者
    // 2. 一次只能有一个所有者
    // 3. 当所有者离开作用域，值将被丢弃
    
    // 变量作用域
    {
        let s = "hello"; // 从此处起，s 开始有效
        // 使用 s
    }   // 此作用域结束，s 不再有效
    
    // String 类型
    let mut s = String::from("hello");
    s.push_str(", world!"); // push_str() 在字符串后追加字面值
    println!("{}", s); // 将打印 `hello, world!`
    
    // 内存和分配
    {
        let s = String::from("hello"); // 从此处起，s 开始有效
        // 使用 s
    } // 此作用域结束，s 不再有效，自动释放
    
    // 移动
    let s1 = String::from("hello");
    let s2 = s1; // s1 移动到 s2
    // println!("{}, world!", s1); // 错误！s1 已失效
    
    // 克隆
    let s1 = String::from("hello");
    let s2 = s1.clone(); // 深拷贝
    println!("s1 = {}, s2 = {}", s1, s2);
    
    // 栈上数据的复制
    let x = 5;
    let y = x; // 复制，因为 i32 实现了 Copy trait
    println!("x = {}, y = {}", x, y);
    
    // 所有权和函数
    let s = String::from("hello");  // s 进入作用域
    takes_ownership(s);             // s 的值移动到函数里
    // println!("{}", s); // 错误！s 已失效
    
    let x = 5;                      // x 进入作用域
    makes_copy(x);                  // x 应该移动函数里，但 i32 是 Copy 的
    println!("{}", x);              // 所以 x 依然有效
    
    // 返回值和作用域
    let s1 = gives_ownership();     // gives_ownership 将返回值移动给 s1
    println!("{}", s1);
    
    let s2 = String::from("hello");
    let s3 = takes_and_gives_back(s2); // s2 移动到函数，返回值移动给 s3
    println!("{}", s3);
}

fn takes_ownership(some_string: String) {
    println!("{}", some_string);
} // 这里，some_string 移出作用域并调用 `drop` 方法

fn makes_copy(some_integer: i32) {
    println!("{}", some_integer);
} // 这里，some_integer 移出作用域

fn gives_ownership() -> String {
    let some_string = String::from("yours");
    some_string
}

fn takes_and_gives_back(a_string: String) -> String {
    a_string
}

// 引用
fn references() {
    let s1 = String::from("hello");
    let len = calculate_length(&s1); // 传递引用
    println!("The length of '{}' is {}.", s1, len);
    
    // 可变引用
    let mut s = String::from("hello");
    change(&mut s);
    println!("{}", s);
    
    // 可变引用的限制
    let mut s = String::from("hello");
    let r1 = &mut s;
    // let r2 = &mut s; // 错误！不能同时有多个可变引用
    println!("{}", r1);
    
    // 可以通过大括号创建新的作用域
    let mut s = String::from("hello");
    {
        let r1 = &mut s;
        println!("{}", r1);
    } // r1 离开作用域，可以重新借用
    let r2 = &mut s;
    println!("{}", r2);
    
    // 悬垂引用
    // let reference_to_nothing = dangle(); // 错误！
}

fn calculate_length(s: &String) -> usize {
    s.len()
} // s 离开作用域。但因为它没有所有权，所以什么也不会发生

fn change(some_string: &mut String) {
    some_string.push_str(", world");
}

// fn dangle() -> &String {
//     let s = String::from("hello");
//     &s
// } // s 离开作用域，被丢弃。其内存被释放。危险！

// 切片
fn slices() {
    let s = String::from("hello world");
    let hello = &s[0..5];
    let world = &s[6..11];
    println!("{} {}", hello, world);
    
    // 切片语法糖
    let s = String::from("hello");
    let slice = &s[0..2];
    let slice = &s[..2];
    
    let len = s.len();
    let slice = &s[3..len];
    let slice = &s[3..];
    
    let slice = &s[..];
    
    // 字符串字面值是切片
    let s: &str = "Hello, world!";
    
    // 数组切片
    let a = [1, 2, 3, 4, 5];
    let slice = &a[1..3];
    println!("{:?}", slice);
}

// ============================================
// 第3节：结构体
// ============================================

#[derive(Debug)]
struct User {
    username: String,
    email: String,
    sign_in_count: u64,
    active: bool,
}

struct Rectangle {
    width: u32,
    height: u32,
}

struct Color(i32, i32, i32);
struct Point(i32, i32, i32);

struct AlwaysEqual;

fn structs() {
    // 创建实例
    let mut user1 = User {
        email: String::from("someone@example.com"),
        username: String::from("someusername123"),
        active: true,
        sign_in_count: 1,
    };
    
    // 修改字段
    user1.email = String::from("anotheremail@example.com");
    
    // 结构体更新语法
    let user2 = User {
        email: String::from("another@example.com"),
        ..user1
    };
    
    // 元组结构体
    let black = Color(0, 0, 0);
    let origin = Point(0, 0, 0);
    
    // 类单元结构体
    let subject = AlwaysEqual;
    
    // 打印结构体
    println!("{:?}", user1);
    println!("{:#?}", user1);
}

// 方法
impl Rectangle {
    fn area(&self) -> u32 {
        self.width * self.height
    }
    
    fn width(&self) -> bool {
        self.width > 0
    }
    
    fn can_hold(&self, other: &Rectangle) -> bool {
        self.width > other.width && self.height > other.height
    }
    
    // 关联函数
    fn square(size: u32) -> Self {
        Self {
            width: size,
            height: size,
        }
    }
}

fn methods() {
    let rect1 = Rectangle {
        width: 30,
        height: 50,
    };
    
    println!(
        "The area of the rectangle is {} square pixels.",
        rect1.area()
    );
    
    if rect1.width() {
        println!("The rectangle has a nonzero width; it is {}", rect1.width);
    }
    
    let rect2 = Rectangle {
        width: 10,
        height: 40,
    };
    let rect3 = Rectangle {
        width: 60,
        height: 45,
    };
    
    println!("Can rect1 hold rect2? {}", rect1.can_hold(&rect2));
    println!("Can rect1 hold rect3? {}", rect1.can_hold(&rect3));
    
    let sq = Rectangle::square(3);
    println!("Square: {} x {}", sq.width, sq.height);
}

// ============================================
// 第4节：枚举和模式匹配
// ============================================

#[derive(Debug)]
enum IpAddr {
    V4(u8, u8, u8, u8),
    V6(String),
}

enum Message {
    Quit,
    Move { x: i32, y: i32 },
    Write(String),
    ChangeColor(i32, i32, i32),
}

impl Message {
    fn call(&self) {
        // 方法体
    }
}

enum Option<T> {
    Some(T),
    None,
}

enum Result<T, E> {
    Ok(T),
    Err(E),
}

fn enums() {
    let four = IpAddr::V4(127, 0, 0, 1);
    let loopback = IpAddr::V6(String::from("::1"));
    
    println!("{:?}", four);
    println!("{:?}", loopback);
    
    let m = Message::Write(String::from("hello"));
    m.call();
    
    // Option
    let some_number = Some(5);
    let some_string = Some("a string");
    let absent_number: Option<i32> = None;
}

// match 控制流
fn match_control() {
    let number = 7;
    
    match number {
        1 => println!("One"),
        2 => println!("Two"),
        3 => println!("Three"),
        4 | 5 | 6 | 7 => println!("Four through seven"),
        8..=10 => println!("Eight through ten"),
        _ => println!("Something else"),
    }
    
    // 绑定值的模式
    let x = Some(5);
    let y = 10;
    
    match x {
        Some(50) => println!("Got 50"),
        Some(y) => println!("Matched, y = {:?}", y),
        _ => println!("Default case, x = {:?}", x),
    }
    
    println!("at the end: x = {:?}, y = {:?}", x, y);
    
    // 解构结构体
    struct Point {
        x: i32,
        y: i32,
    }
    
    let p = Point { x: 0, y: 7 };
    let Point { x: a, y: b } = p;
    assert_eq!(0, a);
    assert_eq!(7, b);
    
    // 解构枚举
    enum Color {
        Rgb(i32, i32, i32),
        Hsv(i32, i32, i32),
    }
    
    let msg = Message::ChangeColor(0, 160, 255);
    
    match msg {
        Message::ChangeColor(Color::Rgb(r, g, b)) => {
            println!("Change color to red {}, green {}, and blue {}", r, g, b);
        }
        Message::ChangeColor(Color::Hsv(h, s, v)) => {
            println!("Change color to hue {}, saturation {}, and value {}", h, s, v);
        }
        _ => (),
    }
}

// if let 控制流
fn if_let() {
    let some_value = Some(3);
    
    // 使用 match
    match some_value {
        Some(3) => println!("three"),
        _ => (),
    }
    
    // 使用 if let
    if let Some(3) = some_value {
        println!("three");
    }
    
    // if let 与 else
    let mut count = 0;
    let coin = Coin::Quarter(UsState::Alaska);
    
    if let Coin::Quarter(state) = coin {
        println!("State quarter from {:?}!", state);
    } else {
        count += 1;
    }
}

#[derive(Debug)]
enum UsState {
    Alabama,
    Alaska,
}

enum Coin {
    Penny,
    Nickel,
    Dime,
    Quarter(UsState),
}

// ============================================
// 第5节：模块系统
// ============================================

// 模块定义
mod front_of_house {
    pub mod hosting {
        pub fn add_to_waitlist() {}
        
        fn seat_at_table() {}
    }
    
    mod serving {
        fn take_order() {}
        
        fn serve_order() {}
        
        fn take_payment() {}
    }
}

pub fn eat_at_restaurant() {
    // 绝对路径
    crate::front_of_house::hosting::add_to_waitlist();
    
    // 相对路径
    front_of_house::hosting::add_to_waitlist();
}

// use 关键字
mod front_of_house2 {
    pub mod hosting {
        pub fn add_to_waitlist() {}
    }
}

use crate::front_of_house2::hosting;

pub fn eat_at_restaurant2() {
    hosting::add_to_waitlist();
}

// use 和 as
use std::fmt::Result;
use std::io::Result as IoResult;

// 重导出
mod front_of_house3 {
    pub mod hosting {
        pub fn add_to_waitlist() {}
    }
}

pub use crate::front_of_house3::hosting;

// 嵌套路径
// use std::cmp::Ordering;
// use std::io;
use std::{cmp::Ordering, io};

// glob 运算符
// use std::collections::*;

// ============================================
// 第6节：泛型
// ============================================

// 泛型函数
fn largest<T: PartialOrd>(list: &[T]) -> &T {
    let mut largest = &list[0];
    
    for item in list {
        if item > largest {
            largest = item;
        }
    }
    
    largest
}

fn generics() {
    let number_list = vec![34, 50, 25, 100, 65];
    let result = largest(&number_list);
    println!("The largest number is {}", result);
    
    let char_list = vec!['y', 'm', 'a', 'q'];
    let result = largest(&char_list);
    println!("The largest char is {}", result);
}

// 泛型结构体
struct PointGeneric<T> {
    x: T,
    y: T,
}

impl<T> PointGeneric<T> {
    fn x(&self) -> &T {
        &self.x
    }
}

// 多个泛型类型参数
struct PointMixed<T, U> {
    x: T,
    y: U,
}

// 泛型枚举
enum OptionGeneric<T> {
    Some(T),
    None,
}

enum ResultGeneric<T, E> {
    Ok(T),
    Err(E),
}

// ============================================
// 第7节：特征
// ============================================

// 定义特征
pub trait Summary {
    fn summarize(&self) -> String;
    
    // 默认实现
    fn summarize_author(&self) -> String {
        String::from("(Read more...)")
    }
}

// 为类型实现特征
pub struct NewsArticle {
    pub headline: String,
    pub location: String,
    pub author: String,
    pub content: String,
}

impl Summary for NewsArticle {
    fn summarize(&self) -> String {
        format!("{}, by {} ({})", self.headline, self.author, self.location)
    }
}

pub struct Tweet {
    pub username: String,
    pub content: String,
    pub reply: bool,
    pub retweet: bool,
}

impl Summary for Tweet {
    fn summarize(&self) -> String {
        format!("{}: {}", self.username, self.content)
    }
}

// 特征作为参数
pub fn notify(item: &impl Summary) {
    println!("Breaking news! {}", item.summarize());
}

// Trait Bound 语法
pub fn notify2<T: Summary>(item: &T) {
    println!("Breaking news! {}", item.summarize());
}

// 多个特征
pub fn notify3(item: &(impl Summary + Display)) {
    // ...
}

// where 子句
fn some_function<T, U>(t: &T, u: &U) -> i32
where
    T: Display + PartialOrd,
    U: Clone + Debug,
{
    // ...
}

// 返回实现了特征的类型
fn returns_summarizable() -> impl Summary {
    Tweet {
        username: String::from("horse_ebooks"),
        content: String::from("of course, as you probably already know, people"),
        reply: false,
        retweet: false,
    }
}

// 使用特征 bound 有条件地实现方法
struct Pair<T> {
    x: T,
    y: T,
}

impl<T> Pair<T> {
    fn new(x: T, y: T) -> Self {
        Self { x, y }
    }
}

impl<T: Display + PartialOrd> Pair<T> {
    fn cmp_display(&self) {
        if self.x >= self.y {
            println!("The largest member is x = {}", self.x);
        } else {
            println!("The largest member is y = {}", self.y);
        }
    }
}

// ============================================
// 第8节：错误处理
// ============================================

// panic!
fn panic_example() {
    // panic!("crash and burn");
    
    let v = vec![1, 2, 3];
    // v[99]; // panic!
}

// Result<T, E>
use std::fs::File;
use std::io::ErrorKind;

fn result_example() {
    let f = File::open("hello.txt");
    
    let f = match f {
        Ok(file) => file,
        Err(error) => match error.kind() {
            ErrorKind::NotFound => match File::create("hello.txt") {
                Ok(fc) => fc,
                Err(e) => panic!("Problem creating the file: {:?}", e),
            },
            other_error => panic!("Problem opening the file: {:?}", other_error),
        },
    };
}

// unwrap 和 expect
use std::fs::File;

fn unwrap_example() {
    let f = File::open("hello.txt").unwrap();
    let f = File::open("hello.txt").expect("Failed to open hello.txt");
}

// 传播错误
use std::io;
use std::io::Read;

fn read_username_from_file() -> Result<String, io::Error> {
    let f = File::open("hello.txt");
    
    let mut f = match f {
        Ok(file) => file,
        Err(e) => return Err(e),
    };
    
    let mut s = String::new();
    
    match f.read_to_string(&mut s) {
        Ok(_) => Ok(s),
        Err(e) => Err(e),
    }
}

// ? 运算符
fn read_username_from_file2() -> Result<String, io::Error> {
    let mut f = File::open("hello.txt")?;
    let mut s = String::new();
    f.read_to_string(&mut s)?;
    Ok(s)
}

// 链式调用
fn read_username_from_file3() -> Result<String, io::Error> {
    let mut s = String::new();
    File::open("hello.txt")?.read_to_string(&mut s)?;
    Ok(s)
}

// 使用 std::fs
use std::fs;

fn read_username_from_file4() -> Result<String, io::Error> {
    fs::read_to_string("hello.txt")
}

// ============================================
// 第9节：并发编程
// ============================================

use std::thread;
use std::time::Duration;
use std::sync::mpsc;
use std::sync::{Mutex, Arc};

fn concurrency() {
    // 创建线程
    thread::spawn(|| {
        for i in 1..10 {
            println!("hi number {} from the spawned thread!", i);
            thread::sleep(Duration::from_millis(1));
        }
    });
    
    for i in 1..5 {
        println!("hi number {} from the main thread!", i);
        thread::sleep(Duration::from_millis(1));
    }
    
    // 等待线程结束
    let handle = thread::spawn(|| {
        for i in 1..10 {
            println!("hi number {} from the spawned thread!", i);
            thread::sleep(Duration::from_millis(1));
        }
    });
    
    for i in 1..5 {
        println!("hi number {} from the main thread!", i);
        thread::sleep(Duration::from_millis(1));
    }
    
    handle.join().unwrap();
    
    // 使用 move 闭包
    let v = vec![1, 2, 3];
    
    let handle = thread::spawn(move || {
        println!("Here's a vector: {:?}", v);
    });
    
    handle.join().unwrap();
    
    // 消息传递
    let (tx, rx) = mpsc::channel();
    
    thread::spawn(move || {
        let vals = vec![
            String::from("hi"),
            String::from("from"),
            String::from("the"),
            String::from("thread"),
        ];
        
        for val in vals {
            tx.send(val).unwrap();
            thread::sleep(Duration::from_secs(1));
        }
    });
    
    for received in rx {
        println!("Got: {}", received);
    }
    
    // 共享状态并发
    let counter = Arc::new(Mutex::new(0));
    let mut handles = vec![];
    
    for _ in 0..10 {
        let counter = Arc::clone(&counter);
        let handle = thread::spawn(move || {
            let mut num = counter.lock().unwrap();
            *num += 1;
        });
        handles.push(handle);
    }
    
    for handle in handles {
        handle.join().unwrap();
    }
    
    println!("Result: {}", *counter.lock().unwrap());
}

// ============================================
// 第10节：智能指针
// ============================================

use std::boxed::Box;
use std::rc::Rc;
use std::cell::RefCell;

fn smart_pointers() {
    // Box<T> 用于堆分配
    let b = Box::new(5);
    println!("b = {}", b);
    
    // 递归类型
    #[derive(Debug)]
    enum List {
        Cons(i32, Box<List>),
        Nil,
    }
    
    use List::{Cons, Nil};
    
    let list = Cons(1, Box::new(Cons(2, Box::new(Cons(3, Box::new(Nil))))));
    println!("{:?}", list);
    
    // Rc<T> 引用计数
    let a = Rc::new(5);
    let b = Rc::clone(&a);
    let c = Rc::clone(&a);
    println!("count after c = {}", Rc::strong_count(&a));
    
    // RefCell<T> 内部可变性
    let value = Rc::new(RefCell::new(5));
    
    let a = Rc::clone(&value);
    let b = Rc::clone(&value);
    
    *value.borrow_mut() += 10;
    
    println!("a = {}, b = {}", a.borrow(), b.borrow());
}

fn main() {
    println!("=== Rust 完整教程 ===");
    
    variables();
    data_types();
    functions();
    control_flow();
    ownership();
    references();
    slices();
    structs();
    methods();
    enums();
    match_control();
    if_let();
    generics();
    concurrency();
    smart_pointers();
    
    println!("=== Rust 完整教程完成 ===");
}
