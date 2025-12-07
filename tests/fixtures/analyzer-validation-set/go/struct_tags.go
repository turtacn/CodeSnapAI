package main

import (
	"encoding/json"
	"fmt"
	"time"
)

// Struct with various tags
type User struct {
	ID        int       `json:"id" db:"user_id" validate:"required"`
	Name      string    `json:"name" db:"full_name" validate:"required,min=2,max=50"`
	Email     string    `json:"email" db:"email_address" validate:"required,email"`
	Age       int       `json:"age" db:"age" validate:"min=0,max=150"`
	CreatedAt time.Time `json:"created_at" db:"created_at"`
	UpdatedAt time.Time `json:"updated_at" db:"updated_at"`
	IsActive  bool      `json:"is_active" db:"is_active" default:"true"`
}

// Struct with embedded fields and tags
type Profile struct {
	User                    // Embedded struct
	Bio        string       `json:"bio,omitempty" db:"biography"`
	Avatar     string       `json:"avatar,omitempty" db:"avatar_url"`
	Settings   UserSettings `json:"settings" db:"-"` // Not stored in DB
	Metadata   interface{}  `json:"metadata,omitempty" db:"metadata,type:jsonb"`
}

type UserSettings struct {
	Theme         string `json:"theme" default:"light"`
	Notifications bool   `json:"notifications" default:"true"`
	Language      string `json:"language" default:"en"`
}

// Struct with complex tags
type Product struct {
	ID          string  `json:"id" bson:"_id" validate:"required"`
	Name        string  `json:"name" bson:"name" validate:"required,min=1,max=100"`
	Description string  `json:"description,omitempty" bson:"description"`
	Price       float64 `json:"price" bson:"price" validate:"required,min=0"`
	Currency    string  `json:"currency" bson:"currency" validate:"required,len=3"`
	Tags        []string `json:"tags,omitempty" bson:"tags"`
	Attributes  map[string]interface{} `json:"attributes,omitempty" bson:"attributes"`
	CreatedBy   string  `json:"created_by" bson:"created_by" validate:"required"`
	CreatedAt   time.Time `json:"created_at" bson:"created_at"`
}

// Generic struct with tags
type Response[T any] struct {
	Data    T      `json:"data"`
	Message string `json:"message,omitempty"`
	Status  int    `json:"status"`
	Error   string `json:"error,omitempty"`
}

// Struct with validation tags
type CreateUserRequest struct {
	Name     string `json:"name" validate:"required,min=2,max=50" example:"John Doe"`
	Email    string `json:"email" validate:"required,email" example:"john@example.com"`
	Password string `json:"password" validate:"required,min=8" example:"secretpassword"`
	Age      int    `json:"age" validate:"min=18,max=100" example:"25"`
}

// Struct with database-specific tags
type Order struct {
	ID          int64     `db:"id,primarykey,autoincrement"`
	UserID      int64     `db:"user_id,notnull" foreign:"users.id"`
	ProductID   int64     `db:"product_id,notnull" foreign:"products.id"`
	Quantity    int       `db:"quantity,notnull,default:1"`
	TotalPrice  float64   `db:"total_price,notnull"`
	Status      string    `db:"status,notnull,default:'pending'" enum:"pending,confirmed,shipped,delivered,cancelled"`
	OrderDate   time.Time `db:"order_date,notnull,default:now()"`
	ShippedDate *time.Time `db:"shipped_date,null"`
}

// Methods for the structs
func (u *User) GetFullName() string {
	return u.Name
}

func (u *User) IsAdult() bool {
	return u.Age >= 18
}

func (p *Product) GetDisplayPrice() string {
	return fmt.Sprintf("%.2f %s", p.Price, p.Currency)
}

func (o *Order) CalculateTotal(unitPrice float64) {
	o.TotalPrice = float64(o.Quantity) * unitPrice
}

// Function that works with tagged structs
func ValidateUser(user User) error {
	// Validation logic would go here
	if user.Name == "" {
		return fmt.Errorf("name is required")
	}
	if user.Email == "" {
		return fmt.Errorf("email is required")
	}
	return nil
}

func main() {
	user := User{
		ID:        1,
		Name:      "John Doe",
		Email:     "john@example.com",
		Age:       30,
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
		IsActive:  true,
	}

	// Convert to JSON to demonstrate tag usage
	jsonData, err := json.Marshal(user)
	if err != nil {
		fmt.Printf("Error marshaling user: %v\n", err)
		return
	}

	fmt.Printf("User JSON: %s\n", string(jsonData))
}